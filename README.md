# CodebaseQA 🦈

**Ask any GitHub repo questions in plain English — and get answers grounded in
the real code, with file-and-line citations.**

CodebaseQA is a full-stack **Code RAG** (retrieval-augmented generation) app.
Point it at a repository; it clones and indexes the source into a
[pgvector](https://github.com/pgvector/pgvector) store, then **Spark** — a
friendly code-analyst assistant — answers questions like *"How does
authentication work?"* or *"Where is the payment logic?"* using semantic search
over the code plus an LLM.

It's built to run **completely free**: embeddings run on-device and the default
LLM (Groq) needs no credit card, so there is nothing that can ever bill you.

<!-- TODO: drop a screenshot or GIF of the app here — e.g. ![CodebaseQA](docs/screenshot.png) -->
<img width="1541" height="719" alt="Screenshot 2026-06-23 at 10 46 57 AM" src="https://github.com/user-attachments/assets/eee2b863-bdd8-422e-8e97-d4679d1a8555" />


## Features

- 🔍 **Semantic code search** over any GitHub repo (pgvector + HNSW index)
- 💬 **Grounded answers with citations** — every claim points back to `path:line`
- 🦈 **Spark**, a friendly assistant that **streams its progress live** (searching → thinking → answering) so the screen is never blank
- 🆓 **Free by default** — on-device embeddings + Groq's free LLM; no credit card, nothing that can be charged
- 🔌 **Swappable providers** — flip the LLM (Groq ⇄ Claude) or embeddings (local ⇄ Voyage) with a single env var
- ⏳ **Live background indexing** with a climbing chunk count and a **cancel** button
- 🛡️ **Safety-minded** — treats repo contents as untrusted data (prompt-injection resistant), per-IP rate limits, and a daily usage budget
- 🌐 **Language-agnostic** — indexes Python, JS/TS, Go, Rust, Java, C/C++, Ruby, and more

## Stack

| Layer      | Tech |
|------------|------|
| Frontend   | React + TypeScript + Vite + Tailwind CSS v4 |
| Backend    | Django + Django REST Framework |
| Vector DB  | Postgres 16 + [pgvector](https://github.com/pgvector/pgvector) |
| Embeddings | **Local** `bge-small-en-v1.5` via fastembed (on-device, 384-dim) — swappable to Voyage |
| LLM        | **Groq** Llama 3.3 70B (free, default) — swappable to Anthropic Claude |

Both AI steps sit behind small provider interfaces, so each is a one-line env
change: the LLM (`apps/chat/services/llm.py`, `LLM_PROVIDER=groq|anthropic`) and
embeddings (`apps/repos/services/embeddings.py`, `EMBED_PROVIDER=local|voyage`).
The defaults — Groq (free, no card) + on-device embeddings (no API at all) —
mean the running demo has **nothing that can ever be charged**.

## How it works

```
GitHub URL ──► clone (shallow) ──► chunk source files ──► embed (local)
                                                              │
                                                              ▼
                                                     pgvector (CodeChunk)
                                                              │
   question ──► embed query ──► cosine-similarity search ─────┘
                                       │
                                       ▼
                       top-k chunks + question ──► LLM (Groq/Claude) ──► grounded answer
```

- Backend: `apps/repos` (ingestion + indexing) and `apps/chat` (retrieval + synthesis).
- Retrieval uses pgvector cosine distance with an HNSW index.

## Prerequisites

- Docker (for Postgres + pgvector)
- Python 3.10+
- Node 20+
- A **free** [Groq API key](https://console.groq.com) — no credit card. This is
  the only key you need; embeddings run on-device with no API at all.
- *(Optional)* an [Anthropic API key](https://console.anthropic.com/) to run on
  Claude (`LLM_PROVIDER=anthropic`), or a [Voyage key](https://www.voyageai.com/)
  for code-specialized embeddings (`EMBED_PROVIDER=voyage`, requires a card).

## Setup

### Quick start (macOS) — one click

Double-click **`start.command`** in Finder. It starts Docker + the database,
does first-run setup automatically (venv, `pip install`, `npm install`,
migrations), then opens a Terminal window each for the backend and frontend and
launches the browser. Double-click **`stop.command`** to shut it all down.

> First run only: if macOS blocks it with a security prompt, right-click
> `start.command` → **Open** once. Also make sure `backend/.env` has your free
> `GROQ_API_KEY`.

The manual steps below do the same thing if you prefer the terminal.

### 1. Database

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then fill in GROQ_API_KEY (the only key needed)

python manage.py migrate
python manage.py runserver    # http://localhost:8000
```

> The pgvector extension is enabled by the first migration
> (`apps/repos/migrations/0001_enable_pgvector.py`).

### 3. Frontend

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

The Vite dev server proxies `/api` to `http://localhost:8000`, so no CORS setup
is needed in development.

## Configuration

All settings live in `backend/.env` (copy from `.env.example`). The defaults are
chosen to be free and to run out of the box — you only *need* `GROQ_API_KEY`.

| Variable | Default | What it does |
|----------|---------|--------------|
| `LLM_PROVIDER` | `groq` | Answer model backend: `groq` (free) or `anthropic` |
| `GROQ_API_KEY` | — | **Required.** Free key from [console.groq.com](https://console.groq.com) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model to use |
| `ANTHROPIC_API_KEY` | — | Required only if `LLM_PROVIDER=anthropic` |
| `EMBED_PROVIDER` | `local` | Embeddings backend: `local` (on-device) or `voyage` |
| `LOCAL_EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | fastembed model (downloads once) |
| `EMBED_DIM` | `384` | Vector dim — must match the model (384 local / 1024 voyage) |
| `MAX_OUTPUT_TOKENS` | `1536` | Cap on each answer's length |
| `RETRIEVAL_TOP_K` | `6` | Code chunks retrieved per question |
| `MAX_CHUNKS_PER_REPO` | `6000` | Cap on chunks embedded per repo |
| `DAILY_TOKEN_BUDGET` | `2000000` | Daily token guard (resets 00:00 UTC) |
| `DAILY_COST_BUDGET_USD` | `2.00` | Daily $ guard (only bites on a paid provider) |
| `THROTTLE_ASK_BURST` / `_DAY` | `15/min` / `200/day` | Per-IP limits on questions |
| `THROTTLE_INDEX_BURST` | `10/hour` | Per-IP limit on indexing |

> Switching `EMBED_PROVIDER` changes the vector dimension, so also set `EMBED_DIM`
> to match and re-run `python manage.py migrate` (the column is altered for you).

## Usage

1. Open http://localhost:5173.
2. Paste a GitHub URL (e.g. `https://github.com/pallets/flask`) and click
   **Index repository**. Indexing runs in the background — the repo appears
   immediately with a live status chip (`cloning` → `indexing` → `ready`), a
   climbing chunk count, and a **cancel** link if you picked the wrong repo.
3. Once **ready**, ask questions in the chat. Answers cite the source chunks
   they were grounded in.

## API

| Method | Path | Purpose |
|--------|------|---------|
| `GET`  | `/api/repositories/` | List indexed repos |
| `POST` | `/api/repositories/` | `{ "url", "branch?" }` — clone + index |
| `POST` | `/api/repositories/{id}/reindex/` | Re-run the pipeline |
| `DELETE` | `/api/repositories/{id}/` | Remove a repo and its chunks |
| `POST` | `/api/ask/` | `{ "repository_id", "question", "top_k?" }` |

## The assistant — "Spark"

Answers come from **Spark**, a sharp, friendly code-analyst persona
(`apps/chat/services/rag.py` → `SYSTEM_PROMPT`). He stays grounded in the
retrieved code, cites `path:line`, and admits when the context doesn't cover a
question rather than guessing.

## Safety & abuse resistance

- **Untrusted-data framing.** Retrieved code and the user's question are passed
  to the LLM as *data to analyze*, wrapped in a `<code_context>` boundary with
  explicit instructions never to obey commands hidden inside them (a repo can
  contain `// ignore previous instructions…` in a comment). Spark also refuses
  off-task/malicious requests and won't reveal the system prompt.
- **Per-IP rate limits** (DRF throttling): asks `15/min` + `200/day`, indexing
  `10/hour`. Tune via `THROTTLE_*` in `.env`.
- Spark has **no tools and no secret access** — the worst case for a crafted repo
  is a wrong answer, not data exfiltration.

## Cost controls — built to be free

The strongest guarantee is structural: **embeddings run on-device (no API), and
the default LLM (Groq) has no credit card on file** — so there is literally
nothing that can bill you. If Groq's free limit is reached it rate-limits or
stops; it never charges. That's the real safeguard, not application code.

On top of that, the app keeps usage bounded anyway:

- **App-level daily budget** (`apps/chat/services/budget.py`): token usage is
  recorded per UTC day; requests are refused once `DAILY_TOKEN_BUDGET` (or, on a
  paid provider, `DAILY_COST_BUDGET_USD`) is hit. On Groq the dollar cost is $0,
  so the token budget is what protects the free-tier quota from abuse.
- `MAX_OUTPUT_TOKENS` caps each answer, `RETRIEVAL_TOP_K` bounds input, and
  `MAX_CHUNKS_PER_REPO` bounds embedding work on large repos.
- Per-IP rate limits (above) stop a single visitor from draining the quota.

If you switch to Claude (`LLM_PROVIDER=anthropic`), use **prepaid credits with
auto-reload OFF** in the [Anthropic Console](https://console.anthropic.com/settings/billing)
for the same can't-be-charged guarantee.

All knobs live in `.env` (see `.env.example`).

## Live status / streaming UX

`POST /api/ask/` streams Server-Sent Events, so the UI is never blank — it shows
each phase live: **diving into the code → found N snippets → Spark is thinking
→ writing answer (tokens stream in)**, then the source list. On Claude, the
"thinking" phase also streams Spark's summarized reasoning into a collapsible
block. See `stream_answer` (backend) and `askStream` + `ChatPanel` (frontend).

## Notes & next steps

- **Indexing runs in a background thread** (`start_indexing`) so the request
  returns immediately and progress streams to the UI; it's cooperatively
  cancellable. For a production deploy, swap the thread for a real task queue
  (Celery / RQ / Django-Q) — the function is already queue-friendly.
- **Chunking is line-window based** and language-agnostic. A natural upgrade is
  AST-aware splitting (tree-sitter) per language.
- Chat is currently stateless (one question → one answer). Conversation history
  / follow-ups would be a straightforward addition.
- The daily budget uses Django's default local-memory cache for throttling;
  for multi-process deploys, point `CACHES` at Redis so limits are shared.

## License

Released under the [MIT License](LICENSE) — free to use, modify, and learn from.
