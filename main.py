import json
import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from database import init_db, create_debate, update_debate, finish_debate, list_debates, get_debate
from agents import (
    stream_agent, stream_judge, stream_factcheck,
    DIFFICULTY_CONFIG,
    pro_system, con_system, judge_system, factcheck_system,
    pro_opening_prompt, con_opening_prompt,
    pro_reb1_prompt, con_reb1_prompt,
    pro_reb2_prompt, con_reb2_prompt,
    pro_closing_prompt, con_closing_prompt,
    judge_prompt, factcheck_prompt,
)

init_db()
app = FastAPI(title="Debate Agents")


def debate_generator(topic: str, difficulty: str):
    cfg = DIFFICULTY_CONFIG.get(difficulty, DIFFICULTY_CONFIG["hard"])
    model = cfg["model"]
    word_limit = cfg["word_limit"]
    max_tokens = cfg["max_tokens"]

    debate_id = create_debate(topic, difficulty)

    def sse(agent: str, chunk: str) -> str:
        return f"data: {json.dumps({'agent': agent, 'chunk': chunk})}\n\n"

    def run_round(agent_key: str, system: str, user: str, use_judge=False, use_factcheck=False):
        """Stream one round, return full text. Yields SSE chunks."""
        full = ""
        if use_judge:
            gen = stream_judge(system, user)
        elif use_factcheck:
            gen = stream_factcheck(system, user)
        else:
            gen = stream_agent(system, user, model, max_tokens)

        for chunk, full_text in gen:
            if chunk:
                yield sse(agent_key, chunk)
            if full_text:
                full = full_text
        return full

    # We can't use return value from a generator, so collect manually
    def collect(agent_key, system, user, use_judge=False, use_factcheck=False):
        full = ""
        if use_judge:
            gen = stream_judge(system, user)
        elif use_factcheck:
            gen = stream_factcheck(system, user)
        else:
            gen = stream_agent(system, user, model, max_tokens)
        for chunk, full_text in gen:
            if chunk:
                yield sse(agent_key, chunk)
            if full_text:
                full = full_text
        yield f"__FULL__{agent_key}:{full}"  # internal sentinel

    # Round 1 — Pro opening
    pro_text = ""
    for item in collect("pro", pro_system(topic, word_limit), pro_opening_prompt(topic)):
        if item.startswith("__FULL__"):
            pro_text = item.split(":", 1)[1]
        else:
            yield item
    if pro_text.startswith("__ERROR__"):
        yield sse("error", "Pro agent timed out."); return
    update_debate(debate_id, pro_opening=pro_text)

    # Round 2 — Con opening
    con_text = ""
    for item in collect("con", con_system(topic, word_limit), con_opening_prompt(topic, pro_text)):
        if item.startswith("__FULL__"):
            con_text = item.split(":", 1)[1]
        else:
            yield item
    if con_text.startswith("__ERROR__"):
        yield sse("error", "Con agent timed out."); return
    update_debate(debate_id, con_opening=con_text)

    # Round 3 — Pro rebuttal 1
    pro_reb1 = ""
    for item in collect("pro_reb1", pro_system(topic, word_limit), pro_reb1_prompt(topic, pro_text, con_text)):
        if item.startswith("__FULL__"):
            pro_reb1 = item.split(":", 1)[1]
        else:
            yield item
    if pro_reb1.startswith("__ERROR__"):
        yield sse("error", "Pro agent timed out."); return
    update_debate(debate_id, pro_reb1=pro_reb1)

    # Round 4 — Con rebuttal 1
    con_reb1 = ""
    for item in collect("con_reb1", con_system(topic, word_limit), con_reb1_prompt(topic, pro_text, con_text, pro_reb1)):
        if item.startswith("__FULL__"):
            con_reb1 = item.split(":", 1)[1]
        else:
            yield item
    if con_reb1.startswith("__ERROR__"):
        yield sse("error", "Con agent timed out."); return
    update_debate(debate_id, con_reb1=con_reb1)

    # Round 5 — Pro rebuttal 2
    pro_reb2 = ""
    for item in collect("pro_reb2", pro_system(topic, word_limit), pro_reb2_prompt(topic, pro_text, con_text, pro_reb1, con_reb1)):
        if item.startswith("__FULL__"):
            pro_reb2 = item.split(":", 1)[1]
        else:
            yield item
    if pro_reb2.startswith("__ERROR__"):
        yield sse("error", "Pro agent timed out."); return
    update_debate(debate_id, pro_reb2=pro_reb2)

    # Round 6 — Con rebuttal 2
    con_reb2 = ""
    for item in collect("con_reb2", con_system(topic, word_limit), con_reb2_prompt(topic, pro_text, con_text, pro_reb1, con_reb1, pro_reb2)):
        if item.startswith("__FULL__"):
            con_reb2 = item.split(":", 1)[1]
        else:
            yield item
    if con_reb2.startswith("__ERROR__"):
        yield sse("error", "Con agent timed out."); return
    update_debate(debate_id, con_reb2=con_reb2)

    # Round 7 — Pro closing
    pro_close = ""
    for item in collect("pro_close", pro_system(topic, word_limit), pro_closing_prompt(topic, pro_text, con_text, pro_reb1, con_reb1, pro_reb2, con_reb2)):
        if item.startswith("__FULL__"):
            pro_close = item.split(":", 1)[1]
        else:
            yield item
    if pro_close.startswith("__ERROR__"):
        yield sse("error", "Pro agent timed out."); return
    update_debate(debate_id, pro_close=pro_close)

    # Round 8 — Con closing
    con_close = ""
    for item in collect("con_close", con_system(topic, word_limit), con_closing_prompt(topic, pro_text, con_text, pro_reb1, con_reb1, pro_reb2, con_reb2, pro_close)):
        if item.startswith("__FULL__"):
            con_close = item.split(":", 1)[1]
        else:
            yield item
    if con_close.startswith("__ERROR__"):
        yield sse("error", "Con agent timed out."); return
    update_debate(debate_id, con_close=con_close)

    # Round 9 — Judge
    judge_text = ""
    for item in collect("judge", judge_system(topic), judge_prompt(topic, pro_text, con_text, pro_reb1, con_reb1, pro_reb2, con_reb2, pro_close, con_close), use_judge=True):
        if item.startswith("__FULL__"):
            judge_text = item.split(":", 1)[1]
        else:
            yield item
    if judge_text.startswith("__ERROR__"):
        yield sse("error", "Judge agent timed out."); return

    # Round 10 — Fact-checker
    factcheck_text = ""
    for item in collect("factcheck", factcheck_system(), factcheck_prompt(topic, pro_text, con_text, pro_reb1, con_reb1, pro_reb2, con_reb2, pro_close, con_close), use_factcheck=True):
        if item.startswith("__FULL__"):
            factcheck_text = item.split(":", 1)[1]
        else:
            yield item

    finish_debate(debate_id, judge_text, factcheck_text)
    yield sse("done", "")


@app.get("/api/debate")
def debate(
    topic: str = Query(..., min_length=3),
    difficulty: str = Query("hard"),
):
    if difficulty not in ("easy", "hard"):
        difficulty = "hard"
    return StreamingResponse(
        debate_generator(topic, difficulty),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/history")
def history():
    rows = list_debates()
    return [dict(r) for r in rows]


@app.get("/api/history/{debate_id}")
def debate_detail(debate_id: int):
    row = get_debate(debate_id)
    if not row:
        raise HTTPException(status_code=404, detail="Debate not found")
    return dict(row)


app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
def index():
    return FileResponse("frontend/index.html")
