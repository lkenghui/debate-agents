import json
import os
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from agents import (
    stream_agent, stream_judge,
    pro_system, con_system, judge_system,
    pro_opening_prompt, con_opening_prompt,
    pro_closing_prompt, con_closing_prompt, judge_prompt,
)

app = FastAPI(title="Debate Agents")


def debate_generator(topic: str):
    def sse(agent: str, chunk: str) -> str:
        return f"data: {json.dumps({'agent': agent, 'chunk': chunk})}\n\n"

    pro_text = ""
    con_text = ""
    pro_close = ""
    con_close = ""

    # Round 1 — Pro opening
    for chunk, full in stream_agent(pro_system(topic), pro_opening_prompt(topic)):
        if chunk:
            pro_text_partial = chunk
            yield sse("pro", chunk)
        if full:
            pro_text = full

    # Round 2 — Con opening
    for chunk, full in stream_agent(con_system(topic), con_opening_prompt(topic, pro_text)):
        if chunk:
            yield sse("con", chunk)
        if full:
            con_text = full

    # Round 3 — Pro closing
    for chunk, full in stream_agent(pro_system(topic), pro_closing_prompt(topic, pro_text, con_text)):
        if chunk:
            yield sse("pro_close", chunk)
        if full:
            pro_close = full

    # Round 4 — Con closing
    for chunk, full in stream_agent(con_system(topic), con_closing_prompt(topic, pro_text, con_text, pro_close)):
        if chunk:
            yield sse("con_close", chunk)
        if full:
            con_close = full

    # Round 5 — Judge verdict
    for chunk, full in stream_judge(
        judge_system(topic),
        judge_prompt(topic, pro_text, con_text, pro_close, con_close),
    ):
        if chunk:
            yield sse("judge", chunk)

    yield sse("done", "")


@app.get("/api/debate")
def debate(topic: str = Query(..., min_length=3)):
    return StreamingResponse(
        debate_generator(topic),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
def index():
    return FileResponse("frontend/index.html")
