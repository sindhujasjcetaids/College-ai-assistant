"""
app.py
------
Flask application entry point for the College AI Student Support Assistant.

Run with:
    python app.py

Then open http://127.0.0.1:5000 in your browser.
"""

import os
from flask import Flask, request, jsonify, render_template, session, send_from_directory

import memory
import chat
from rag_engine import engine, KB_DIR

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

memory.init_db()


def _get_session_id():
    if "session_id" not in session:
        session["session_id"] = memory.new_session_id()
    return session["session_id"]


@app.route("/")
def index():
    _get_session_id()
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    session_id = _get_session_id()
    result = chat.handle_turn(session_id, message)
    return jsonify(result)


@app.route("/api/history", methods=["GET"])
def api_history():
    session_id = _get_session_id()
    history = memory.get_history(session_id)
    return jsonify({"history": history})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    session_id = _get_session_id()
    memory.clear_history(session_id)
    return jsonify({"status": "cleared"})


@app.route("/api/search", methods=["GET"])
def api_search():
    """Direct retrieval endpoint (useful for debugging / power users)."""
    query = request.args.get("q", "")
    category = request.args.get("category")
    if not query:
        return jsonify({"error": "Missing query parameter 'q'."}), 400
    results = engine.retrieve(query, top_k=6, category=category)
    return jsonify({"results": results})


@app.route("/api/documents", methods=["GET"])
def api_documents():
    """List indexed knowledge base documents."""
    files = sorted(os.listdir(KB_DIR))
    return jsonify({"documents": files, "total_chunks": len(engine.chunks)})


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "chunks_indexed": len(engine.chunks)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    print(f"\nCollege AI Student Support Assistant running at http://127.0.0.1:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
