# Agentic RAG System — DeepSeek + FastAPI

A **production-style Agentic Retrieval-Augmented Generation (RAG) system** built with FastAPI, ChromaDB, HuggingFace DeepSeek LLM, and LangGraph.

This project is designed to demonstrate **real AI engineering practices**.

---
### Sample Outputs
![1767339747982](image/Readme/1767339747982.png)
![1767339760644](image/Readme/1767339760644.png)

## What This Project Demonstrates

This system goes beyond basic RAG and showcases:

- Robust **PDF ingestion & vectorization**
- **Grounded RAG** (hallucination-aware prompting)
- **Agentic reasoning** using LangGraph
- **Tool introspection** (decision transparency)
- **Conversation memory** (multi-turn context)
- Clean **FastAPI service architecture**
- Simple UI for querying, ingestion, and observability
- **LLM-as-judge RAG evaluation** (faithfulness + answer relevancy)
---

## High-Level Architecture
![1767339773627](image/Readme/1767339773627.png)


---

## Core Components

### Ingestion & Vectorization
- PDFs are parsed, chapter-detected, chunked, and embedded
- Stored in **ChromaDB**
- Deduplication prevents re-indexing
- Metadata includes:
  - book
  - chapter
  - domain
  - source path

**Key files**
- `rag_engine.py`
- `ingestion_service.py`
- `settings.py`

---

### Retrieval-Augmented Generation (RAG)

- Semantic retrieval using embeddings
- Retrieved chunks are passed verbatim
- LLM is **strictly grounded** on retrieved context
- No external knowledge allowed

**Key file**
- `llm_service.py`

---

### Agentic Reasoning (LangGraph)

Instead of a linear pipeline, the system uses an **agent** that:

- Retrieves relevant chunks
- Evaluates **coverage quality**
- Chooses an execution path:
  - `answer` → direct answer
  - `synthesize` → merge partial information

This prevents hallucination while preserving answer quality.

**Key file**
- `agent_service.py`

---

### Agent Decision Flow
The agent **never blocks answers** — it only changes *how* the answer is generated.
![1767337005903](image/Readme/1767337005903.png)
---

### Tool Introspection (Observability)

For every query, the system exposes:

- `coverage`: DIRECT / PARTIAL
- `path_taken`: answer / synthesize

This is visible via:
- API response
- UI

This makes agent behavior **transparent and debuggable**.

---

### Conversation Memory

- Session-scoped memory
- Short-term (last N turns)
- Used only for reasoning continuity
- **Never embedded or stored in vector DB**

Enables:
- Follow-up questions
- Progressive explanations
- Reduced repetition

**Key file**
- `memory_service.py`

---

## User Interface

Single-page FastAPI UI provides:

- Ask questions
- Ingest all PDFs
- View knowledge summary
- View agent introspection
- Persistent session handling

**Key file**
- `ui.py`

### RAG Evaluation — LLM-as-Judge
 
The system includes a built-in evaluation pipeline that measures answer quality
using **DeepSeek as the judge LLM** — the same model powering the RAG pipeline itself.
 
Two Ragas-equivalent metrics are computed on any set of test questions:
 
| Metric | What it measures | Target |
|---|---|---|
| **Faithfulness** | Are all claims in the answer grounded in retrieved context? | > 0.85 |
| **Answer Relevancy** | Does the answer actually address what was asked? | > 0.80 |
 
**How it works:**
 
- For each test question, the system runs the full live pipeline — retrieval + agent
- DeepSeek judges each answer against the retrieved context (faithfulness)
- DeepSeek also rates whether the answer addressed the original question (answer relevancy)
- Scores are averaged across all test questions and returned with a pass/needs_review status
 
**Why LLM-as-judge instead of Ragas directly:**
 
Ragas 0.2.x uses Pydantic v2 schemas in its prompts which are incompatible with
open-source models like DeepSeek — the model echoes the schema instead of filling it.
This implementation uses the same scoring logic as Ragas internally, bypassing the
dependency conflict while keeping the evaluation concept identical.
 
**Key file**
- `eval_service.py`
 
**API endpoint**
- `POST /api/eval`
 
---

## How to Run

### Install dependencies
```bash
pip install -r requirements.txt
```
 
### Set your HuggingFace token
```bash
export HUGGINGFACEHUB_API_TOKEN=your_token_here 
- **Required finegraned token only**
```
 
### Start the server
```bash
uvicorn app.main:app --reload
```
 
### Run RAG evaluation
Navigate to `http://127.0.0.1:8000`, click **Run RAG Evaluation**, enter test questions
(one per line), and click **Run Evaluation**. Scores are returned in real time.
 
---
 
## Project Structure
 
```
app/
├── main.py               # FastAPI app entry point
├── api.py                # All API endpoints including /eval
├── ui.py                 # Single-page browser UI
├── settings.py           # Config — paths, chunk size, top-k
├── rag_engine.py         # PDF ingestion + semantic retrieval
├── ingestion_service.py  # Multi-format ingestion (PDF/DOCX/TXT/URL)
├── vector_store.py       # ChromaDB + HuggingFace embeddings
├── llm_service.py        # DeepSeek via HF InferenceClient
├── agent_service.py      # LangGraph agentic reasoning pipeline
├── memory_service.py     # Session-scoped conversation memory
└── eval_service.py       # LLM-as-judge RAG evaluation (NEW)
```