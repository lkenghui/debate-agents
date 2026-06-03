import sqlite3
import os
import re
from datetime import datetime, timezone

DB_PATH = os.getenv("DB_PATH", "debates.db")

ALLOWED_COLUMNS = {
    "pro_opening", "con_opening", "pro_reb1", "con_reb1",
    "pro_reb2", "con_reb2", "pro_close", "con_close",
    "judge", "factcheck", "winner", "finished_at",
}


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS debates (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                topic       TEXT    NOT NULL,
                difficulty  TEXT    NOT NULL DEFAULT 'hard',
                started_at  TEXT    NOT NULL,
                finished_at TEXT,
                pro_opening TEXT,
                con_opening TEXT,
                pro_reb1    TEXT,
                con_reb1    TEXT,
                pro_reb2    TEXT,
                con_reb2    TEXT,
                pro_close   TEXT,
                con_close   TEXT,
                judge       TEXT,
                factcheck   TEXT,
                winner      TEXT
            )
        """)


def create_debate(topic: str, difficulty: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO debates (topic, difficulty, started_at) VALUES (?, ?, ?)",
            (topic, difficulty, datetime.now(timezone.utc).isoformat()),
        )
        return cur.lastrowid


def update_debate(debate_id: int, **fields):
    safe = {k: v for k, v in fields.items() if k in ALLOWED_COLUMNS}
    if not safe:
        return
    set_clause = ", ".join(f"{k} = ?" for k in safe)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE debates SET {set_clause} WHERE id = ?",
            (*safe.values(), debate_id),
        )


def finish_debate(debate_id: int, judge_text: str, factcheck_text: str):
    winner = _extract_winner(judge_text)
    update_debate(
        debate_id,
        finished_at=datetime.now(timezone.utc).isoformat(),
        judge=judge_text,
        factcheck=factcheck_text,
        winner=winner,
    )


def _extract_winner(judge_text: str) -> str | None:
    m = re.search(r"verdict.*?\b(PRO|CON)\b", judge_text, re.IGNORECASE | re.DOTALL)
    return m.group(1).upper() if m else None


def list_debates(limit: int = 30) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, topic, difficulty, started_at, winner "
            "FROM debates WHERE finished_at IS NOT NULL "
            "ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()


def get_debate(debate_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM debates WHERE id = ?", (debate_id,)
        ).fetchone()
