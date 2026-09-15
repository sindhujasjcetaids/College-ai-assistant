"""
rag_engine.py
--------------
A lightweight Retrieval-Augmented Generation (RAG) engine for the
College AI Student Support Assistant.

It works fully OFFLINE using TF-IDF + cosine similarity for retrieval
(scikit-learn), so the app runs out-of-the-box without any paid API key.

If the user sets an ANTHROPIC_API_KEY (or OPENAI_API_KEY) environment
variable, the engine will optionally use that LLM to generate a more
natural final answer from the retrieved context (see llm_client.py).
Without a key, the engine still produces a solid, well-formatted answer
using extractive summarization of the retrieved chunks.
"""

import os
import re
import glob
import json
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from llm_client import generate_llm_answer, llm_is_configured


KB_DIR = os.path.join(os.path.dirname(__file__), "knowledge_base")

CATEGORY_MAP = {
    "regulations.txt": "Regulations",
    "syllabus.txt": "Syllabus",
    "faqs.txt": "FAQ",
    "notices.txt": "Notice",
}


def _split_into_chunks(text: str, filename: str) -> List[Dict]:
    """Split a knowledge base document into retrievable chunks.

    Documents use blank-line separated paragraphs / entries as natural
    chunk boundaries (each SECTION, COURSE, Q&A pair, or NOTICE block).
    """
    raw_chunks = re.split(r"\n\s*\n", text.strip())
    chunks = []
    for i, chunk in enumerate(raw_chunks):
        chunk = chunk.strip()
        if not chunk:
            continue
        chunks.append(
            {
                "id": f"{filename}::{i}",
                "source": filename,
                "category": CATEGORY_MAP.get(filename, "General"),
                "text": chunk,
            }
        )
    return chunks


class RAGEngine:
    """TF-IDF based retrieval engine over the college knowledge base."""

    def __init__(self, kb_dir: str = KB_DIR):
        self.kb_dir = kb_dir
        self.chunks: List[Dict] = []
        self.vectorizer: TfidfVectorizer = None
        self.matrix = None
        self._build_index()

    def _load_documents(self) -> List[Dict]:
        all_chunks = []
        for path in sorted(glob.glob(os.path.join(self.kb_dir, "*.txt"))):
            filename = os.path.basename(path)
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            all_chunks.extend(_split_into_chunks(text, filename))
        return all_chunks

    def _build_index(self):
        self.chunks = self._load_documents()
        corpus = [c["text"] for c in self.chunks]
        if not corpus:
            self.vectorizer = None
            self.matrix = None
            return
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_df=0.9,
        )
        self.matrix = self.vectorizer.fit_transform(corpus)

    def reload(self):
        """Rebuild the index (call after documents are added/updated)."""
        self._build_index()

    def retrieve(self, query: str, top_k: int = 4, category: str = None) -> List[Dict]:
        """Return the top_k most relevant chunks for a query."""
        if not self.chunks or self.vectorizer is None:
            return []

        query_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self.matrix).flatten()

        ranked_idx = sims.argsort()[::-1]
        results = []
        for idx in ranked_idx:
            score = float(sims[idx])
            if score <= 0.02:
                continue
            chunk = self.chunks[idx]
            if category and chunk["category"].lower() != category.lower():
                continue
            results.append({**chunk, "score": round(score, 4)})
            if len(results) >= top_k:
                break
        return results

    def answer(self, query: str, history: List[Dict] = None, top_k: int = 4) -> Dict:
        """Full RAG pipeline: retrieve relevant chunks then compose an answer."""
        retrieved = self.retrieve(query, top_k=top_k)

        if llm_is_configured():
            answer_text = generate_llm_answer(query, retrieved, history or [])
        else:
            answer_text = self._extractive_answer(query, retrieved)

        return {
            "answer": answer_text,
            "sources": [
                {
                    "source": r["source"],
                    "category": r["category"],
                    "snippet": r["text"][:220] + ("..." if len(r["text"]) > 220 else ""),
                    "score": r["score"],
                }
                for r in retrieved
            ],
            "used_llm": llm_is_configured(),
        }

    @staticmethod
    def _extractive_answer(query: str, retrieved: List[Dict]) -> str:
        """Fallback answer composer used when no LLM API key is configured.

        Produces a clear, readable answer built directly from the most
        relevant retrieved chunks (extractive RAG - no hallucination risk).
        """
        if not retrieved:
            return (
                "I couldn't find anything specific about that in the "
                "regulations, syllabus, FAQs, or notices I have indexed. "
                "Could you rephrase your question, or ask about attendance, "
                "grading, exams, fees, hostel rules, a specific course, or "
                "recent notices?"
            )

        lines = []
        top = retrieved[0]
        lines.append(f"Based on the {top['category']} document, here's what I found:\n")
        for r in retrieved[:3]:
            bullet = r["text"].replace("\n", " ")
            if len(bullet) > 400:
                bullet = bullet[:400].rsplit(" ", 1)[0] + "..."
            lines.append(f"• ({r['category']}) {bullet}")

        lines.append(
            "\nIf this doesn't fully answer your question, try being more "
            "specific (e.g. mention the course code, semester, or exact policy name)."
        )
        return "\n".join(lines)


# Singleton instance used by the Flask app
engine = RAGEngine()
