# Sift Performance Report

Date: 2026-09-29 · Target machine: MacBook Air M3, 8 GB unified memory

**How this was produced:** a read-through of the backend (`backend/app/**`) and the SwiftUI frontend's indexing and polling code, plus web research on alternatives. It also uses the measured baseline from 2026-09-17 (6-file folder: 24.5 s wall, ~85% of it in Ollama round-trips, both models resident at ~3.3 GB combined, machine already swapping at idle).
**What this is not:** nothing was profiled in this session, and none of the alternatives were benchmarked on your hardware. Impact estimates below are informed guesses, ranked by likelihood. Section 5 says how to confirm them.

---

## 1. Why the Mac becomes unusable

There are two compounding causes. Neither is Sift's Python code being slow.

1. **Memory pressure.** The 8 GB machine was already at ~7.4 GB used with 4.4 GB of swap before Sift ran. Ollama then loads *both* models (`qwen3-embedding:0.6b` ≈ 2.4 GB, `gemma3:1b` ≈ 0.9 GB) and keeps them resident, and the Python process adds ~450 MB. Once macOS starts swapping, the whole UI stutters, not just Sift.
2. **Unthrottled, serial, full-speed work.** Indexing runs flat out with nothing pacing the GPU/CPU. Each file goes through an LLM summary, then an embedding call, so the two models alternate constantly. Metal GPU load from Ollama competes with the window compositor, so the UI itself lags.

The measured 6-file run is too small to show this. A real folder multiplies the per-file cost, and the issues in section 2 make that multiplication worse than it needs to be.

---

## 2. Findings in the current code (ranked by likely impact)

| # | Finding | Where | Effect |
|---|---|---|---|
| 1 | **The folder walk has no exclusions.** It takes every `.json/.py/.xml/.toml/.c/...` under the folder, including `node_modules`, `.venv`, `.git`, `build/`, and hidden dirs. There is also no file-size cap. | `indexer.py:48-51` | Pointing at a project folder can queue tens of thousands of junk files. Probably the single largest cause of "unusable". `.env` files are also embedded and stored, which is a privacy smell. |
| 2 | **The entire document is sent to the LLM for the one-line summary**, with no truncation. This happens once per file, before chunking. | `fileParser.py:86`, `151-153`, `llamaService.py:75-81` | Long prefill on a 1B model for every file. Ollama will silently clamp to its `num_ctx`, which I did not verify (I don't know which end it drops). Summaries are also the main reason the two models keep alternating. |
| 3 | **All chunks of a file go to Ollama in one `embed` call.** | `embedder.py:21` | A 300-page PDF becomes thousands of chunks in one request, giving a large memory and latency spike with no chance to yield. |
| 4 | **One `table.add` per chunk.** Each call commits a new LanceDB version and fragment. No `optimize()` is ever called. | `databaseService.py:52-55` | A 219-chunk run makes 219 commits. LanceDB docs say per-call overhead grows with fragment count, and recommend batching plus periodic `optimize()`. |
| 5 | **No incremental indexing.** Re-adding a folder re-parses, re-summarizes, and re-embeds every file and inserts duplicate rows. No mtime/hash check, no delete-before-insert. | `indexer.py:56-67` | Repeated work on every run. The index also grows without bound and search quality drops from duplicates. |
| 6 | **`POST /process` is synchronous and long-lived.** The frontend's request timeout is 300 s. A second POST while one is running starts a second concurrent indexer sharing `Parser` state. | `app.py:48-58`, `IndexingService.swift` | Large folders will time out client-side while the backend keeps going. Double-adding a folder doubles the load. |
| 7 | **Search and indexing fight over Ollama.** A query embed waits behind batch embeds. Each search then makes two sequential 1B generations (summary, then rank) after the vector lookup. | `search.py:22-23` | Search latency spikes during indexing. Steady-state search pays two LLM calls. |
| 8 | **`GetMetadataForFiles` and `GetAllMetadata` load the whole metadata table into Python on every call.** Vector search is hardcoded `limit(5)` and ignores `numFiles`. | `databaseService.py:73-84`, `99` | Cost grows linearly with index size on every search and every `/files` call. |
| 9 | **Small correctness issues that also waste work.** `ParseText` appends `"\n"` after lines that already end in `\n`, which inflates chunks. `Chunker` can raise `IndexError` when no boundary character exists before the end of text, because it indexes `text[charIndex]` unbounded. `pymupdf4llm` is imported but unused, and `is_complex()` parses each PDF once before the real parse. | `fileParser.py:97-105`, `chunker.py:42-46`, `fileParser.py:7`, `112` | Minor CPU and startup cost; the crash would abort a whole folder run. |
| 10 | **Status polling every 1 s forever**, even when idle. | `IndexingStatusMonitor.swift` | Small. Back off to ~5 s when `isProcessing` is false. |

---

## 3. Alternatives and trade-offs

### A. Tune Ollama (no architecture change) — low effort, moderate gain
- `OLLAMA_MAX_LOADED_MODELS=1` and a short `keep_alive` (e.g. 30 s, or `keep_alive=0` on the summarizer) so the two models never sit resident together. Per-request `keep_alive` overrides the env var.
- Set `num_ctx` explicitly per call (e.g. ~1024 for embedding, ~4096 for chat). I suspect part of the 2.4 GB for a 0.6B embedding model is KV-cache allocation for a large default context. **This is a hypothesis to test with `ollama ps`, not a measured fact.**
- Flash attention / quantized KV cache (`OLLAMA_FLASH_ATTENTION`, `OLLAMA_KV_CACHE_TYPE`) trims memory further.
- **Drawback:** reloading a model costs seconds on each swap, so this only pays off if the pipeline is restructured to avoid alternating models (see B).

### B. Restructure the pipeline into phases — low/medium effort, largest structural win
Phase 1 walks, parses, chunks, and embeds, with only the embedding model loaded, so files become searchable early. Phase 2 (optional, idle-time) generates summaries with the chat model, after the embedding model is unloaded.
- Cap summary input (first ~2–4k characters), or drop index-time summaries and derive a summary from the top chunks at search time.
- **Drawback:** ranking loses the per-file summary until phase 2 finishes, and there are two state machines to track (status API needs a "summarizing" state).

### C. Throttle indexing as a background job — low/medium effort, biggest *perceived* win
The goal is bounded resource use, not minimum wall-clock time.
- Small embedding batches (e.g. 16–32 chunks) with a short sleep between them, so the GPU yields to the compositor.
- Pause or slow down under memory pressure (`memory_pressure` / `sysctl kern.memorystatus_vm_pressure_level`), on battery, or in Low Power Mode.
- Run the Python indexer under `taskpolicy -c background`. Per [ss64](https://ss64.com/mac/taskpolicy.html) and [Eclectic Light](https://eclecticlight.co/2025/05/09/what-is-quality-of-service-and-how-does-it-matter/), background QoS pins threads to E-cores and can throttle disk I/O.
- **Drawbacks:** indexing takes longer. QoS only affects CPU work in *your* process (parsing, OCR). Ollama's Metal inference runs in Ollama's own process, so batching and pacing are the real GPU levers. I did not verify how far `taskpolicy` helps for a process Ollama launches.

### D. Reduce the work — low effort, high gain
Skip `node_modules/.git/.venv/build` and hidden dirs; add a size cap; skip `.env`; make OCR opt-in or lower-DPI; index incrementally by (path, mtime, size); delete a file's old rows before re-inserting. **Drawback:** some files won't be searchable unless the user opts in.

### E. Smaller embedding model — medium effort (forces a full re-index)
| Model | Size | Dims | Note |
|---|---|---|---|
| all-minilm | ~46 MB | 384 | Tiny; short max sequence length, so check that 1100-char chunks fit |
| bge-small-v1.5 | ~0.24 GB RAM | 384 | Reported ~467 emb/s; a common default for general text |
| nomic-embed-text | ~274 MB | 768 | Longer context |
| embeddinggemma | ~622 MB | 768 | Strong on some domains, weaker on CS papers per one comparison |
| qwen3-embedding:0.6b (current) | ~2.4 GB resident | 1024 | Best quality of these; heaviest |

Figures come from search-result snippets ([SurrealDB comparison](https://surrealdb.com/blog/embedding-models-comparison), [Morph list](https://www.morphllm.com/ollama-embedding-models); my attempt to fetch the Morph page was rate-limited, so treat the numbers as unverified). **Drawbacks:** lower retrieval quality, and `databaseService.py` hardcodes 1024 dims, so switching means a schema change and a re-index. Run a mini-eval on your own files before committing, as the sources themselves recommend. Also note `dimensions=1024` in `embedder.py:21` is the native size, so it currently saves nothing; a smaller Matryoshka dimension would shrink the DB and search cost but not model compute (verify support in the model card).

### F. Embed in-process instead of via Ollama (fastembed / ONNX Runtime / sentence-transformers) — medium effort
The model lives in Sift's process, loads only while indexing, and is freed after. This removes one resident model and one HTTP hop. ONNX Runtime has a [CoreML execution provider](https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html) for the Neural Engine, but it notes dynamic input shapes can hurt performance. **Drawbacks:** it is CPU-bound by default and would take cores from the UI unless throttled (C). It adds heavy Python dependencies, and I found no M3 benchmark comparing it to Ollama's Metal path, so this is unproven.

### G. Different runtime (MLX / llama.cpp directly) — higher effort, uncertain fit
Third-party posts claim MLX is 15–30% faster and ~10% lighter than Ollama ([example](https://willitrunai.com/blog/mlx-vs-ollama-apple-silicon-benchmarks)). But Ollama's own [MLX preview](https://ollama.com/blog/mlx) currently covers one large model and asks for >32 GB of memory, so it does nothing for an 8 GB Air. Running `llama-server --embedding` directly would give finer control (context, threads, batch) at the cost of shipping and supervising a binary. **Not recommended until A–D are done.**

### H. Simplify the search path — low/medium effort
Drop the LLM ranker (a 1B model's 1–10 scores are weak signal) and rank by vector distance, optionally fused with LanceDB full-text search (hybrid). Make the summary optional or streamed, and skip it while indexing is running. **Drawbacks:** lose the "reason" text per result, and FTS needs an index. Hybrid retrieval generally helps exact-term queries, but that's general knowledge, not something measured on Sift.

### I. LanceDB hygiene — low effort
One batched `add` per file (or per several files), `optimize()` after a run, and filtered metadata queries (`where filePath IN ...`) instead of loading the whole table. A vector index isn't needed at small scale; brute-force is fine until the row count gets large.

### J. Wildcard: Apple's on-device embeddings (NaturalLanguage framework), from the Swift side
The OS manages the model and memory, with no Ollama for embeddings at all. **Unverified in this session**, and likely lower quality with a Swift/macOS-only coupling. Worth a small spike only if the Ollama-based options can't fit in 8 GB.

---

## 4. Recommended order

| Step | Change | Effort | Expected effect |
|---|---|---|---|
| 1 | Folder exclusions, size cap, skip `.env` (D) | ~1 hr | Likely the largest single reduction in total work |
| 2 | Batch DB inserts, chunked embedding (16–32/call), fix `IndexError` (I, 3, 9) | ~2 hr | Removes spikes and per-chunk commit overhead |
| 3 | Incremental indexing (mtime/size) + one-indexer-at-a-time guard + return from `/process` immediately (D, 5, 6) | ~half day | No repeat work; no timeout on big folders |
| 4 | Two-phase pipeline; truncate summary input (B) | ~half day | Only one model resident during indexing |
| 5 | Ollama env/`num_ctx`/`keep_alive` tuning (A) | ~1 hr, then measure | Smaller model footprint; verify the KV-cache hypothesis |
| 6 | Pacing + memory-pressure/battery aware throttle (C) | ~half day | Machine stays usable during indexing |
| 7 | Evaluate a smaller embedding model on your own files (E) | ~half day | Possibly ~2 GB less memory, at some quality cost |
| 8 | Simplify search: drop LLM ranker, optional summary (H) | ~half day | Faster, more predictable search |

Steps 1–3 need no model changes and are worth doing first. Step 7 is the biggest trade-off, so decide it with data.

---

## 5. How to verify (measure before and after each step)

Use a realistic folder of a few hundred files plus at least one large PDF, not the 6-file test set.
- `vm_stat 1` or Activity Monitor's Memory Pressure graph: watch for yellow/red and swap growth.
- `ollama ps` during a run: model sizes, and whether both are resident.
- Per-stage timers around parse, summarize, embed, and DB insert in `Indexer.process_file`.
- `memory_pressure` before and after, plus how long the UI takes to respond to ⌥Space during indexing.
- Track file count, chunk count, and DB fragment count, to confirm fixes 1, 4, and 5 do what they should.

---

## Sources
- [Ollama FAQ (keep_alive, MAX_LOADED_MODELS, NUM_PARALLEL)](https://docs.ollama.com/faq)
- [Ollama MLX blog](https://ollama.com/blog/mlx)
- [MLX vs Ollama benchmarks (third-party)](https://willitrunai.com/blog/mlx-vs-ollama-apple-silicon-benchmarks)
- [Embedding model comparison, SurrealDB](https://surrealdb.com/blog/embedding-models-comparison)
- [LanceDB performance tips](https://docs.lancedb.com/performance)
- [taskpolicy reference](https://ss64.com/mac/taskpolicy.html)
- [QoS on Apple silicon, Eclectic Light](https://eclecticlight.co/2025/05/09/what-is-quality-of-service-and-how-does-it-matter/)
- [ONNX Runtime CoreML EP](https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html)
