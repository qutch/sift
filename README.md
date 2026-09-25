# Sift

**Search your files by what they mean, not just what they're named. Everything runs on your own machine.**

Sift is a local semantic file search tool for macOS. Point it at a folder and it reads your documents, notes, PDFs, and code, then builds a vector index using AI models that run locally. When you search, Sift finds the files whose *content* matches what you asked for, ranks them by relevance, and writes a short summary of what it found. It works like Spotlight, but it understands what your files are about.

Nothing leaves your computer. There are no cloud APIs, no accounts, and no telemetry. All models run through [Ollama](https://ollama.com), and the index is stored in a local [LanceDB](https://lancedb.com) database.

> **Status:** Early development. The backend indexing and search pipeline works end to end. The macOS frontend UI is built but isn't connected to the backend yet (it uses mock data). See [Roadmap](#roadmap--whats-next).

---

## Table of Contents

- [Features](#features)
- [How It Works](#how-it-works)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [API](#api)
- [Roadmap / What's Next](#roadmap--whats-next)

---

## Features

- **Semantic search:** finds files by meaning. For example, "notes about sorting algorithms" can match a file that never uses the word "sorting".
- **Fully local and private:** embedding, summarizing, and ranking all run on local models through Ollama.
- **Multi-format parsing:** handles plain text (`.txt`, `.md`), source code and config files (`.py`, `.java`, `.c`, `.cpp`, `.json`, `.xml`, `.env`, `.toml`), and PDFs.
- **Smart PDF handling:** detects scanned or complex pages and uses OCR only when needed. Simple PDFs go through a faster text parser.
- **AI file summaries:** each indexed file gets a one-sentence, keyword-rich summary.
- **LLM re-ranking:** results from the vector search are re-scored from 1 to 10 by a local LLM, using structured JSON output. Each score comes with a short reason.
- **Search summaries:** each search returns a natural-language summary of the matching content.
- **Spotlight-style macOS app:** a menu bar app with a global hotkey (<kbd>⌥ Option</kbd> + <kbd>Space</kbd>) that opens a floating search panel with keyboard navigation.

---

## How It Works

### Indexing pipeline

```
 Folder
   │
   ▼
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐
│ Indexer  │──▶│  Parser  │──▶│ Chunker  │──▶│ Embedder │──▶│  DBService   │
│ walk dir │   │ text/pdf │   │ overlap  │   │ qwen3    │   │  LanceDB     │
│ filter by│   │ metadata │   │ chunks,  │   │ embedding│   │ sift-vectors │
│ extension│   │ + summary│   │ word-safe│   │ 1024-dim │   │ sift-metadata│
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────────┘
                    │
                    ▼
              Summarizer (gemma3:1b)
```

1. **Indexer** (`indexer.py`) walks a folder and collects files that match the target extensions.
2. **Parser** (`fileParser.py`) extracts text and file metadata (size, created, last edited, last opened), then asks the **Summarizer** for a one-line summary.
3. **Chunker** (`chunker.py`) removes escape characters and splits the text into overlapping chunks. Chunk boundaries are extended to the next word or punctuation break so words aren't cut in half.
4. **Embedder** (`embedder.py`) batch-embeds the chunks with `qwen3-embedding:0.6b`, producing 1024-dimensional vectors.
5. **DBService** (`databaseService.py`) stores the chunk vectors and the per-file metadata in two LanceDB tables.

### Search pipeline

```
 Query ──▶ embed query ──▶ LanceDB vector search (top 5 chunks)
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
          Summarizer (gemma3:1b)            Ranker (llama3.2:3b)
          summary of the matches            score each file 1–10
                     │                    (with file summaries as context)
                     └───────────────┬───────────────┘
                                     ▼
                     { "summary": ..., "ranking": [...] }
```

`Searcher.SearchAndRank()` (`search.py`) embeds the query, pulls the closest chunks from LanceDB, and then does two things with them:

- Summarizes the matched content in relation to the query.
- Groups the chunks by file, adds each file's stored summary, and has the Ranker score every file. The ranker uses a Pydantic schema to force structured output, which keeps small local models reliable.

### Database schema

| Table           | Columns |
|-----------------|---------|
| `sift-vectors`  | `vector` (float32[1024]), `filePath`, `chunkIndex`, `chunkText` |
| `sift-metadata` | `fileType`, `fileName`, `filePath`, `summary`, `size`, `lastOpened`, `lastEdited`, `createdAt` |

---

## Tech Stack

### Backend (Python)

| Tool | Purpose |
|------|---------|
| **Python 3.13** | Language |
| **[uv](https://docs.astral.sh/uv/)** | Dependency and environment management |
| **[FastAPI](https://fastapi.tiangolo.com)** | HTTP API for the frontend |
| **[Ollama](https://ollama.com)** | Local model runtime (embeddings and chat) |
| **[LanceDB](https://lancedb.com)** + PyArrow | Embedded vector database |
| **[LiteParse](https://pypi.org/project/liteparse/)** | PDF parsing with optional OCR |
| **PyMuPDF / pymupdf4llm** | PDF tooling |
| **Pydantic** | Structured LLM output for ranking |

### Models (via Ollama)

| Model | Role |
|-------|------|
| `qwen3-embedding:0.6b` | Chunk and query embeddings (1024 dims) |
| `gemma3:1b` | File summaries and search-result summaries |
| `llama3.2:3b` | Relevance ranking (a reasoning task, so it uses a larger model) |

### Frontend (macOS)

| Tool | Purpose |
|------|---------|
| **Swift / SwiftUI** | UI (`MenuBarExtra`, search view) |
| **AppKit** | Borderless floating `NSPanel`, `NSWorkspace` for opening files |
| **Carbon HIToolbox** | Global hotkey registration (no Accessibility permission needed) |
| **Observation** (`@Observable`) | View model state |
| **Xcode**, macOS 26 deployment target | Build |

---

## Project Structure

```
sift/
├── backend/
│   ├── pyproject.toml            # Python deps (managed with uv)
│   ├── uv.lock
│   └── app/
│       ├── app.py                # FastAPI app & routes
│       └── services/
│           ├── indexer.py        # Walks folders, filters by file type
│           ├── fileParser.py     # Text / code / PDF parsing + metadata
│           ├── chunker.py        # Text cleaning + overlapping chunking
│           ├── embedder.py       # Ollama embeddings → Vector objects
│           ├── databaseService.py# LanceDB tables, inserts, vector search
│           ├── llamaService.py   # Summarizer, Ranker, ChunkSummarizer
│           ├── search.py         # Searcher: search → summarize → rank
│           ├── watcher.py        # (planned) filesystem watcher
│           └── classes/
│               ├── File.py       # Parsed file + metadata + chunks/vectors
│               ├── Vector.py     # A single embedded chunk
│               └── FileType.py   # File type enum
└── frontend/
    └── sift-frontend/            # Xcode project (macOS menu bar app)
        └── sift-frontend/
            ├── App.swift         # MenuBarExtra entry point
            ├── AppDelegate.swift # Accessory app setup + ⌥Space hotkey
            ├── HotKey.swift      # Carbon global hotkey wrapper
            ├── SearchPanel.swift # Floating Spotlight-style panel
            ├── ContentView.swift # Search bar + results list UI
            └── SearchModel.swift # View model, debounced search, mock service
```

---

## Getting Started

### Prerequisites

- macOS (the frontend targets macOS 26; the backend uses `st_birthtime`, which is macOS/BSD only)
- [Ollama](https://ollama.com/download), installed and running
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Xcode (for the frontend)

### 1. Pull the models

```bash
ollama pull qwen3-embedding:0.6b
ollama pull gemma3:1b
ollama pull llama3.2:3b
```

### 2. Install backend dependencies

```bash
cd backend
uv sync
```

### 3. Configure paths

The database location is currently hardcoded in `backend/app/services/databaseService.py`:

```python
self.uri = "/users/hutch/desktop/example_lancedb"
```

Change it to a directory on your machine before running.

### 4. Run the API

```bash
cd backend/app
uv run fastapi dev app.py
```

The API runs at `http://127.0.0.1:8000`, and interactive docs are at `/docs`.

> The backend is still being restructured, so some imports and routes may need adjusting before this runs cleanly. See the roadmap below.

### 5. Run the macOS app

Open `frontend/sift-frontend/sift-frontend.xcodeproj` in Xcode and run it. A magnifying glass icon appears in the menu bar. Press <kbd>⌥ Option</kbd> + <kbd>Space</kbd> to open the search panel. Use <kbd>↑</kbd>/<kbd>↓</kbd> to move between results, <kbd>Return</kbd> to open a file, and <kbd>Esc</kbd> to close the panel.

---

## API

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/search/{search_query}` | Semantic search. Returns a summary and a ranked file list |
| `GET` | `/file/{file_path}` | Returns stored metadata for a file |

Example response from `/search/data structures`:

```json
{
  "summary": "Your notes cover linked lists, trees, and Big-O analysis...",
  "ranking": [
    { "filePath": "/Users/you/notes/dsa.md", "relevance": 9, "reason": "Directly covers data structures." },
    { "filePath": "/Users/you/notes/cs-midterm.pdf", "relevance": 6, "reason": "Mentions trees and graphs." }
  ]
}
```

---

## Roadmap / What's Next

### Connect the frontend to the backend
- [ ] Replace `MockSearchService` with a real service that calls `GET /search/{query}` (`SearchModel.searchRequest` is still a `TODO`).
- [ ] Map the backend's `ranking` and `summary` response to `FileResult`, and show the search summary in the panel.
- [ ] Load real **Recent Files** from the backend (using `lastOpened` metadata) instead of mock data.
- [ ] Launch and manage the Python backend from the Mac app, or run it as a background service.

### Indexing
- [ ] Add a real indexing entry point. The test driver was removed from `indexer.py`, so there's currently no way to trigger indexing. Options are an API route (e.g. `POST /index`) or a CLI command.
- [ ] Let users choose which folders to index from the frontend.
- [ ] Implement `watcher.py` to re-index files automatically when they're created, edited, or deleted.
- [ ] Skip files that haven't changed, and remove stale vectors and metadata when a file is re-indexed or deleted.
- [ ] Add `.docx` support (`ParseWord` is a stub, and `.docx` is currently sent to the PDF parser).
- [ ] Add image support (`ParseImage` is a stub). This would need OCR or a vision model for captions.

### Backend cleanup and fixes
- [ ] Fix the `open_file` route in `app.py` (it uses `@app(...)` instead of an HTTP method decorator, and its path conflicts with `GET /file/{file_path}`).
- [ ] Make `GET /file/{file_path}` pass a list to `GetMetadataForFiles`.
- [ ] Make imports consistent (`services.*` vs. sibling imports) so the API starts from one entry point.
- [ ] Move hardcoded paths (the DB location) and model names into a config file or environment variables.
- [ ] Fix `ChunkSummarizer` referencing `Summarizer.summaryLevel`, or remove it if it's no longer needed.
- [ ] Replace `print` debugging with proper logging, and add error handling around Ollama calls.

### Search quality and performance
- [ ] Make the number of results configurable (it's currently fixed at 5 chunks).
- [ ] Filter searches by file type, date, or folder using the metadata table.
- [ ] Tune chunk size and overlap (currently 100 characters with 20 overlap).
- [ ] Reduce memory and latency. Ollama inference and keeping several models loaded at once are the main costs.

### Testing and packaging
- [ ] Add unit tests for the chunker, parser, and search pipeline.
- [ ] Package Sift as a single installable macOS app.
