"""
llm_client.py
--------------
Optional LLM integration layer.

The assistant works fully offline (extractive RAG) by default.
If you want more natural, synthesized answers, set one of these
environment variables before running the app:

    export ANTHROPIC_API_KEY="sk-ant-..."
    # or
    export OPENAI_API_KEY="sk-..."

When configured, generate_llm_answer() will call the respective API
to turn the retrieved knowledge-base chunks into a fluent answer.
No key is required for the app to function.
"""

import os
from typing import List, Dict

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


def llm_is_configured() -> bool:
    return bool(ANTHROPIC_API_KEY or OPENAI_API_KEY)


SYSTEM_PROMPT = (
    "You are a helpful College Student Support Assistant. Answer the "
    "student's question using ONLY the provided context snippets from "
    "the college's regulations, syllabus, FAQs, and notices. If the "
    "context does not contain the answer, say you don't have that "
    "information and suggest who/where the student could ask. Be "
    "concise, friendly, and cite which document (Regulations / "
    "Syllabus / FAQ / Notice) the information came from."
)


def _build_context_block(retrieved: List[Dict]) -> str:
    if not retrieved:
        return "No relevant context was found in the knowledge base."
    blocks = []
    for r in retrieved:
        blocks.append(f"[{r['category']} - {r['source']}]\n{r['text']}")
    return "\n\n---\n\n".join(blocks)


def generate_llm_answer(query: str, retrieved: List[Dict], history: List[Dict]) -> str:
    context = _build_context_block(retrieved)

    history_text = ""
    for turn in history[-6:]:
        role = "Student" if turn.get("role") == "user" else "Assistant"
        history_text += f"{role}: {turn.get('content', '')}\n"

    user_message = (
        f"Conversation so far:\n{history_text}\n"
        f"Context from college documents:\n{context}\n\n"
        f"Student's question: {query}\n\n"
        "Answer the question clearly and cite the source document type."
    )

    if ANTHROPIC_API_KEY:
        return _call_anthropic(user_message)
    if OPENAI_API_KEY:
        return _call_openai(user_message)
    return "LLM not configured."


def _call_anthropic(user_message: str) -> str:
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        return "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )
    except Exception as e:
        return f"(LLM call failed, falling back to retrieved context) Error: {e}"


def _call_openai(user_message: str) -> str:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=600,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"(LLM call failed, falling back to retrieved context) Error: {e}"
