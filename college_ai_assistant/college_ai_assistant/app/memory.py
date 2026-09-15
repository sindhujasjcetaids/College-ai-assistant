"""
memory.py
---------
Lightweight persistent conversation memory using SQLite.

Each browser session gets a session_id (stored in a cookie). All turns
(user + assistant messages) are stored so the assistant can recall
earlier context ("what did I just ask you?", multi-turn follow-ups)
even across page reloads / server restarts.
"""

import os
import sqlite3
import uuid
from contextlib import contextmanager
from typing import List, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "memory", "conversations.db")


def _ensure_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@contextmanager
def get_conn():
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_used TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                student_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def new_session_id() -> str:
    return str(uuid.uuid4())


def ensure_session(session_id: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sessions (session_id) VALUES (?)", (session_id,)
        )


def add_message(session_id: str, role: str, content: str, tool_used: str = None):
    ensure_session(session_id)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, tool_used) VALUES (?, ?, ?, ?)",
            (session_id, role, content, tool_used),
        )


def get_history(session_id: str, limit: int = 50) -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, tool_used, created_at FROM messages "
            "WHERE session_id = ? ORDER BY id ASC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def clear_history(session_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))


def set_student_name(session_id: str, name: str):
    ensure_session(session_id)
    with get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET student_name = ? WHERE session_id = ?", (name, session_id)
        )


def get_student_name(session_id: str) -> str:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT student_name FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    return row["student_name"] if row and row["student_name"] else None
