import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

FAST_MODEL = "claude-haiku-4-5-20251001"
JUDGE_MODEL = "claude-sonnet-4-6"


def stream_agent(system_prompt: str, user_prompt: str):
    """Yields (text_chunk, full_text) — full_text only non-empty on the last yield."""
    full_text = ""
    with client.messages.stream(
        model=FAST_MODEL,
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for chunk in stream.text_stream:
            full_text += chunk
            yield chunk, ""
    yield "", full_text


def stream_judge(system_prompt: str, user_prompt: str):
    """Same as stream_agent but uses the more capable judge model."""
    full_text = ""
    with client.messages.stream(
        model=JUDGE_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for chunk in stream.text_stream:
            full_text += chunk
            yield chunk, ""
    yield "", full_text


def pro_system(topic: str) -> str:
    return (
        f"You are a skilled, persuasive debater arguing IN FAVOUR of this proposition: '{topic}'. "
        "Make 2-3 sharp, well-reasoned arguments. Be confident and direct. 150-200 words max."
    )


def con_system(topic: str) -> str:
    return (
        f"You are a skilled, persuasive debater arguing AGAINST this proposition: '{topic}'. "
        "Make 2-3 sharp, well-reasoned arguments. Be confident and direct. 150-200 words max."
    )


def judge_system(topic: str) -> str:
    return (
        f"You are an impartial debate judge evaluating a debate on: '{topic}'. "
        "Assess both sides purely on argument quality, logic, and evidence. "
        "Declare a winner (Pro or Con) and explain why in 150-200 words. "
        "Be decisive — you must pick a winner."
    )


def pro_opening_prompt(topic: str) -> str:
    return f"Make your opening argument FOR the proposition: {topic}"


def con_opening_prompt(topic: str, pro_text: str) -> str:
    return (
        f"Your opponent just argued FOR '{topic}':\n\n{pro_text}\n\n"
        "Now make your opening argument AGAINST this proposition. Directly rebut their points."
    )


def pro_closing_prompt(topic: str, pro_text: str, con_text: str) -> str:
    return (
        f"Debate topic: '{topic}'\n\n"
        f"Your opening argument (PRO):\n{pro_text}\n\n"
        f"Opponent's rebuttal (CON):\n{con_text}\n\n"
        "Give a strong closing argument. Address their points and reinforce yours. 100-150 words."
    )


def con_closing_prompt(topic: str, pro_text: str, con_text: str, pro_close: str) -> str:
    return (
        f"Debate topic: '{topic}'\n\n"
        f"PRO opening:\n{pro_text}\n\n"
        f"Your CON opening:\n{con_text}\n\n"
        f"PRO closing:\n{pro_close}\n\n"
        "Give a strong closing argument. Address their closing and seal your case. 100-150 words."
    )


def judge_prompt(topic: str, pro_text: str, con_text: str, pro_close: str, con_close: str) -> str:
    return (
        f"Debate topic: '{topic}'\n\n"
        f"PRO opening:\n{pro_text}\n\n"
        f"CON opening:\n{con_text}\n\n"
        f"PRO closing:\n{pro_close}\n\n"
        f"CON closing:\n{con_close}\n\n"
        "Evaluate the debate and declare a winner."
    )
