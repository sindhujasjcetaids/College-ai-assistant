"""
chat.py
-------
Orchestrates a single chat turn:
  1. Load conversation memory for the session
  2. Try deterministic tools (GPA calc, attendance calc, etc.)
  3. Run RAG retrieval over the knowledge base
  4. Compose the final answer (tool result + retrieved context)
  5. Persist the turn to memory
"""

import re
from typing import Dict

import memory
import tools
from rag_engine import engine


GREETING_PATTERNS = re.compile(r"^\s*(hi|hello|hey|good morning|good evening|good afternoon)\b", re.IGNORECASE)
NAME_PATTERN = re.compile(r"\bmy name is ([A-Za-z][A-Za-z\s]{1,30})", re.IGNORECASE)
THANKS_PATTERN = re.compile(r"^\s*(thanks|thank you|thx|ty)\b", re.IGNORECASE)
WHO_AM_I_PATTERN = re.compile(r"\b(what('?s| is) my name|who am i)\b", re.IGNORECASE)


def handle_turn(session_id: str, user_message: str) -> Dict:
    user_message = user_message.strip()
    memory.add_message(session_id, "user", user_message)

    # --- lightweight conversational shortcuts -------------------------
    name_match = NAME_PATTERN.search(user_message)
    if name_match:
        name = name_match.group(1).strip().split()[0].capitalize()
        memory.set_student_name(session_id, name)
        reply = f"Nice to meet you, {name}! I'm your College Student Support Assistant. Ask me about regulations, your syllabus, FAQs, or recent notices."
        memory.add_message(session_id, "assistant", reply)
        return {"answer": reply, "sources": [], "tool_used": None}

    if WHO_AM_I_PATTERN.search(user_message):
        student_name = memory.get_student_name(session_id)
        if student_name:
            reply = f"You told me your name is {student_name}! How can I help you further?"
        else:
            reply = "You haven't told me your name yet — feel free to share it, or just ask your question directly."
        memory.add_message(session_id, "assistant", reply)
        return {"answer": reply, "sources": [], "tool_used": None}

    if THANKS_PATTERN.match(user_message):
        reply = "You're welcome! Let me know if you have any other questions about college regulations, courses, or notices."
        memory.add_message(session_id, "assistant", reply)
        return {"answer": reply, "sources": [], "tool_used": None}

    if GREETING_PATTERNS.match(user_message) and len(user_message.split()) <= 4:
        student_name = memory.get_student_name(session_id)
        greeting = f"Hello {student_name}! " if student_name else "Hello! "
        reply = (
            greeting
            + "I'm your AI Student Support Assistant. I can help with academic "
            "regulations, syllabus details, FAQs, and the latest notices. What would you like to know?"
        )
        memory.add_message(session_id, "assistant", reply)
        return {"answer": reply, "sources": [], "tool_used": None}

    # --- 1) try deterministic tools ------------------------------------
    tool_name, tool_result = tools.try_tools(user_message)
    if tool_name:
        memory.add_message(session_id, "assistant", tool_result, tool_used=tool_name)
        return {"answer": tool_result, "sources": [], "tool_used": tool_name}

    # --- 2) RAG retrieval + answer composition --------------------------
    history = memory.get_history(session_id, limit=12)
    rag_result = engine.answer(user_message, history=history)

    memory.add_message(session_id, "assistant", rag_result["answer"], tool_used="rag")

    return {
        "answer": rag_result["answer"],
        "sources": rag_result["sources"],
        "tool_used": "rag",
        "used_llm": rag_result.get("used_llm", False),
    }
