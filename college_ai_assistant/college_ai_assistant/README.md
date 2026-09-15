# Campus Desk — AI Student Support Assistant

A fully functional web app that answers college-related questions from
**regulations, syllabus, FAQs, and notices**, built with a
**RAG + Tools + Memory** architecture.

- **RAG** — TF‑IDF + cosine-similarity retrieval over a chunked knowledge
  base (`app/knowledge_base/*.txt`), fully offline, no API key required.
- **Tools** — deterministic helpers the assistant calls automatically:
  a GPA/CGPA calculator, an attendance-eligibility checker, and a date
  lookup, all wired into `app/tools.py`.
- **Memory** — every conversation turn is persisted per browser session
  in a local SQLite database (`app/memory/conversations.db`), so the
  assistant remembers your name and earlier context.

It works completely out of the box with no external API keys. If you
want more fluent, LLM-generated answers on top of the retrieved
context, you can optionally plug in an Anthropic or OpenAI key (see
below) — the app will automatically switch to LLM-generated answers.

---

## 1. Quick start

```bash
cd college_ai_assistant/app
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

That's it — the knowledge base is pre-loaded with sample college
regulations, a semester syllabus, FAQs, and notices, so you can start
chatting immediately.

## 2. Project structure

```
college_ai_assistant/
├── README.md
└── app/
    ├── app.py              # Flask entry point & API routes
    ├── chat.py             # Orchestrates tools + RAG + memory per turn
    ├── rag_engine.py        # TF-IDF retrieval engine
    ├── llm_client.py         # Optional Anthropic/OpenAI integration
    ├── tools.py              # GPA calculator, attendance checker, etc.
    ├── memory.py             # SQLite-backed conversation memory
    ├── requirements.txt
    ├── knowledge_base/
    │   ├── regulations.txt
    │   ├── syllabus.txt
    │   ├── faqs.txt
    │   └── notices.txt
    ├── memory/                # SQLite DB created at runtime
    ├── templates/
    │   └── index.html
    └── static/
        ├── css/style.css
        └── js/chat.js
```

## 3. Customizing the knowledge base

Add or edit `.txt` files inside `app/knowledge_base/`. Each blank-line
separated paragraph becomes a retrievable chunk, so write your
regulations/notices/FAQs as clearly separated entries (see the
existing files for the pattern). The filename determines the display
category:

| Filename          | Category shown in the UI |
|--------------------|--------------------------|
| `regulations.txt`  | Regulations              |
| `syllabus.txt`      | Syllabus                 |
| `faqs.txt`           | FAQ                      |
| `notices.txt`        | Notice                   |

Add any other `.txt` file and it will be indexed under "General".
Restart the app (or call `engine.reload()`) after editing files.

## 4. Built-in tools

The assistant automatically detects when to use a tool instead of pure
retrieval:

- **GPA calculator** — try: `Calculate my GPA: A+ 4 credits, A 3 credits, B+ 4 credits`
- **Attendance checker** — try: `I attended 60 out of 80 classes, am I eligible?`
- **Date lookup** — try: `What is today's date?`

Add new tools in `app/tools.py` by defining a `matches()` and `run()`
pair and registering them in the `TOOLS` list.

## 5. Enabling LLM-generated answers (optional)

By default, answers are composed extractively (directly from the
retrieved document chunks) — this is deterministic, requires no
network access, and never hallucinates. For more natural, fluent
answers, set an API key before starting the app:

```bash
# Option A: Anthropic Claude
export ANTHROPIC_API_KEY="sk-ant-..."
pip install anthropic

# Option B: OpenAI
export OPENAI_API_KEY="sk-..."
pip install openai

python app.py
```

The app automatically detects the key and switches modes — no code
changes needed.

## 6. API endpoints

| Method | Endpoint         | Description                             |
|--------|-------------------|------------------------------------------|
| GET    | `/`                | Chat UI                                  |
| POST   | `/api/chat`         | Send a message, get an answer            |
| GET    | `/api/history`       | Get this session's conversation history |
| POST   | `/api/reset`          | Clear this session's memory             |
| GET    | `/api/search?q=...`    | Raw retrieval results (debugging)     |
| GET    | `/api/documents`        | List indexed knowledge base files   |
| GET    | `/api/health`             | Health check                      |

## 7. Notes on production deployment

- Set a strong `FLASK_SECRET_KEY` environment variable.
- Turn off debug mode (`FLASK_DEBUG=0`).
- Put the app behind a real WSGI server (gunicorn/uWSGI) and a reverse
  proxy (nginx) rather than the Flask dev server.
- Consider swapping the SQLite memory store for Postgres/Redis if you
  expect concurrent multi-instance deployment.
