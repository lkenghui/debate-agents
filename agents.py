import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"), timeout=90.0)

DIFFICULTY_CONFIG = {
    "easy": {"model": "claude-haiku-4-5-20251001", "word_limit": 150, "max_tokens": 350},
    "hard": {"model": "claude-sonnet-4-6",          "word_limit": 300, "max_tokens": 700},
}
JUDGE_MODEL   = "claude-sonnet-4-6"
FACTCHECK_MODEL = "claude-haiku-4-5-20251001"


def stream_agent(system_prompt: str, user_prompt: str, model: str, max_tokens: int):
    """Yields (chunk, "") during streaming, then ("", full_text) on completion."""
    full_text = ""
    try:
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for chunk in stream.text_stream:
                full_text += chunk
                yield chunk, ""
        yield "", full_text
    except (anthropic.APITimeoutError, anthropic.APIConnectionError) as e:
        yield "", f"__ERROR__:{e}"


def stream_judge(system_prompt: str, user_prompt: str):
    full_text = ""
    try:
        with client.messages.stream(
            model=JUDGE_MODEL,
            max_tokens=1200,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for chunk in stream.text_stream:
                full_text += chunk
                yield chunk, ""
        yield "", full_text
    except (anthropic.APITimeoutError, anthropic.APIConnectionError) as e:
        yield "", f"__ERROR__:{e}"


def stream_factcheck(system_prompt: str, user_prompt: str):
    full_text = ""
    try:
        with client.messages.stream(
            model=FACTCHECK_MODEL,
            max_tokens=600,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for chunk in stream.text_stream:
                full_text += chunk
                yield chunk, ""
        yield "", full_text
    except (anthropic.APITimeoutError, anthropic.APIConnectionError) as e:
        yield "", f"__ERROR__:{e}"


# ── System prompts ────────────────────────────────────────────────────────────

def pro_system(topic: str, word_limit: int) -> str:
    return (
        f"You are a skilled, persuasive debater arguing IN FAVOUR of: '{topic}'. "
        f"Make sharp, well-reasoned arguments. Be confident and direct. {word_limit} words max."
    )


def con_system(topic: str, word_limit: int) -> str:
    return (
        f"You are a skilled, persuasive debater arguing AGAINST: '{topic}'. "
        f"Make sharp, well-reasoned arguments. Be confident and direct. {word_limit} words max."
    )


def judge_system(topic: str) -> str:
    return (
        f"You are an impartial debate judge evaluating a structured debate on: '{topic}'. "
        "Evaluate both sides purely on argument quality. Use this EXACT format:\n\n"
        "## Logic & Evidence\n"
        "PRO: X/10 — one sentence. CON: X/10 — one sentence.\n\n"
        "## Argument Structure\n"
        "PRO: X/10 — one sentence. CON: X/10 — one sentence.\n\n"
        "## Rhetoric & Persuasion\n"
        "PRO: X/10 — one sentence. CON: X/10 — one sentence.\n\n"
        "## Verdict\n"
        "State the winner (PRO or CON) and explain in 2-3 sentences why they won. Be decisive."
    )


def factcheck_system() -> str:
    return (
        "You are a neutral fact-checker. Review the debate transcript and identify up to 5 "
        "specific factual claims that are questionable, unverifiable, or demonstrably false. "
        "Format each finding as:\n"
        "- [PRO/CON] \"exact claim\" — your assessment (1 sentence)\n"
        "If all claims appear reasonable, say so briefly."
    )


# ── User prompts ──────────────────────────────────────────────────────────────

def pro_opening_prompt(topic: str) -> str:
    return f"Make your opening argument FOR: {topic}"


def con_opening_prompt(topic: str, pro_text: str) -> str:
    return (
        f"Your opponent argued FOR '{topic}':\n\n{pro_text}\n\n"
        "Make your opening argument AGAINST this proposition. Directly rebut their key points."
    )


def pro_reb1_prompt(topic: str, pro_text: str, con_text: str) -> str:
    return (
        f"Debate topic: '{topic}'\n\n"
        f"Your opening (PRO):\n{pro_text}\n\n"
        f"Opponent's opening (CON):\n{con_text}\n\n"
        "Give your first rebuttal. Attack the weakest point in CON's argument directly."
    )


def con_reb1_prompt(topic: str, pro_text: str, con_text: str, pro_reb1: str) -> str:
    return (
        f"Debate topic: '{topic}'\n\n"
        f"PRO opening:\n{pro_text}\n\n"
        f"Your opening (CON):\n{con_text}\n\n"
        f"PRO's rebuttal:\n{pro_reb1}\n\n"
        "Give your first rebuttal. Counter PRO's rebuttal and reinforce your position."
    )


def pro_reb2_prompt(topic: str, pro_text: str, con_text: str, pro_reb1: str, con_reb1: str) -> str:
    return (
        f"Debate topic: '{topic}'\n\n"
        f"PRO opening:\n{pro_text}\n\n"
        f"CON opening:\n{con_text}\n\n"
        f"Your first rebuttal (PRO):\n{pro_reb1}\n\n"
        f"CON's first rebuttal:\n{con_reb1}\n\n"
        "Give your second rebuttal. Press the most damaging gap in CON's argument."
    )


def con_reb2_prompt(topic: str, pro_text: str, con_text: str, pro_reb1: str, con_reb1: str, pro_reb2: str) -> str:
    return (
        f"Debate topic: '{topic}'\n\n"
        f"PRO opening:\n{pro_text}\n\n"
        f"CON opening:\n{con_text}\n\n"
        f"PRO rebuttal 1:\n{pro_reb1}\n\n"
        f"Your rebuttal 1 (CON):\n{con_reb1}\n\n"
        f"PRO rebuttal 2:\n{pro_reb2}\n\n"
        "Give your second rebuttal. Expose the flaw in PRO's latest argument and seal your position."
    )


def pro_closing_prompt(topic: str, pro_text: str, con_text: str, pro_reb1: str, con_reb1: str, pro_reb2: str, con_reb2: str) -> str:
    return (
        f"Debate topic: '{topic}'\n\n"
        f"PRO opening:\n{pro_text}\n\nCON opening:\n{con_text}\n\n"
        f"PRO reb 1:\n{pro_reb1}\n\nCON reb 1:\n{con_reb1}\n\n"
        f"PRO reb 2:\n{pro_reb2}\n\nCON reb 2:\n{con_reb2}\n\n"
        "Give your closing statement. Summarise your strongest points and leave a lasting impression."
    )


def con_closing_prompt(topic: str, pro_text: str, con_text: str, pro_reb1: str, con_reb1: str, pro_reb2: str, con_reb2: str, pro_close: str) -> str:
    return (
        f"Debate topic: '{topic}'\n\n"
        f"PRO opening:\n{pro_text}\n\nCON opening:\n{con_text}\n\n"
        f"PRO reb 1:\n{pro_reb1}\n\nCON reb 1:\n{con_reb1}\n\n"
        f"PRO reb 2:\n{pro_reb2}\n\nCON reb 2:\n{con_reb2}\n\n"
        f"PRO closing:\n{pro_close}\n\n"
        "Give your closing statement. Counter PRO's closing and end with your strongest argument."
    )


def judge_prompt(topic: str, pro_text: str, con_text: str, pro_reb1: str, con_reb1: str,
                 pro_reb2: str, con_reb2: str, pro_close: str, con_close: str) -> str:
    return (
        f"Debate topic: '{topic}'\n\n"
        f"PRO Opening:\n{pro_text}\n\nCON Opening:\n{con_text}\n\n"
        f"PRO Rebuttal 1:\n{pro_reb1}\n\nCON Rebuttal 1:\n{con_reb1}\n\n"
        f"PRO Rebuttal 2:\n{pro_reb2}\n\nCON Rebuttal 2:\n{con_reb2}\n\n"
        f"PRO Closing:\n{pro_close}\n\nCON Closing:\n{con_close}\n\n"
        "Evaluate the debate and declare a winner."
    )


def factcheck_prompt(topic: str, pro_text: str, con_text: str, pro_reb1: str, con_reb1: str,
                     pro_reb2: str, con_reb2: str, pro_close: str, con_close: str) -> str:
    return (
        f"Debate topic: '{topic}'\n\n"
        f"PRO Opening:\n{pro_text}\n\nCON Opening:\n{con_text}\n\n"
        f"PRO Rebuttal 1:\n{pro_reb1}\n\nCON Rebuttal 1:\n{con_reb1}\n\n"
        f"PRO Rebuttal 2:\n{pro_reb2}\n\nCON Rebuttal 2:\n{con_reb2}\n\n"
        f"PRO Closing:\n{pro_close}\n\nCON Closing:\n{con_close}\n\n"
        "Fact-check the claims above."
    )
