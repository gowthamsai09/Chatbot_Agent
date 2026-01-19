This Project will be updated frequently with new features

Test Application here: - https://personalized-knowledge-assistant.onrender.com
It take few minutes to load the application as server goes to sleep after inactivity. 

Once server is live kindly provide hugging face token to proceed further.
Creating Hugging Face Token: - https://huggingface.co/settings/tokens  (Create with read access)

# Agentic Knowledge Assistant — DeepSeek + FastAPI

This project is a production-style Agentic Knowledge Assistant that combines Retrieval-Augmented Generation (RAG) with agentic decision-making using LangGraph.
Unlike basic RAG demos, this system is designed to behave like a controlled AI agent:
It refuses to hallucinate.
It explains how an answer was produced.
It adapts its reasoning strategy based on context coverage.

---
### Sample Outputs
![1767339747982](image/Readme/1767339747982.png)
![1767339760644](image/Readme/1767339760644.png)

## What This Project Demonstrates

This system goes beyond standard RAG and showcases:
* Multi-format ingestion (PDFs + live web URLs)
* Intelligent chunking with deduplication
* Cloud-hosted vector storage (Qdrant Cloud)
* Metadata-indexed retrieval (document-level & domain-level filtering)
* Agentic reasoning using LangGraph
* Hallucination-aware answering
* Transparent agent introspection
* Session-scoped conversation memory
---

## High-Level Architecture
![1768841932939](image/Readme/1768841932939.png)


---

## Core Components

### Ingestion & Vectorization
The system supports ingesting:
- PDFs
- DOCX / text files
- Live web URLs (HTML parsed via BeautifulSoup)
## Processing pipeline:
- Content extraction.
- Chapter/section detection.
- Recursive chunking
- Deduplication using content hashing
- Embedding via Hugging Face Inference API
- Storage in Qdrant Cloud
- Each chunk is stored with rich metadata:
  - document_id
  - document_name
  - domain
  - source (upload / url)
  - chapter
  - content_hash
- Payload indexes are created in Qdrant for:
  - metadata.document_id
  - metadata.domain
This enables precise filtering without scanning the full vector space.

**Key files**
- `rag_engine.py`
- `ingestion_service.py`
- `vector_store.py`
- `settings.py`

---

### Retrieval-Augmented Generation (RAG)
- Semantic similarity search using Qdrant
- Optional filters:
  - domain-specific
  - document-specific
  - Retrieved chunks are passed
- The LLM is explicitly constrained to use only retrieved context
- If relevant information is missing, the system fails safely instead of hallucinating.

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
![1768842373236](image/Readme/1768842373236.png)
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
- File and URL ingestion
- Domain selection
- Ask-about-this-document mode
- Global knowledge querying
- Agent introspection visibility
- Session persistence

**Key file**
- `ui.py`

---

### Deployment & Production Learnings
- Deployed on Render with GitHub-based CI/CD
- Migrated from local ChromaDB to Qdrant Cloud to overcome memory limits
- Switched to remote Hugging Face embeddings to reduce server RAM usage
- Implemented payload indexing to support filtered vector search
- Resolved multiple issues that only surfaced in cloud deployment:
  - Out Of Memory errors
  - Missing payload indexes
  - Inference latency

---

![](https://komarev.com/ghpvc/?username=gowthamsai09)

## How to Run

### Install dependencies
```bash

pip install -r requirements.txt

export HUGGINGFACEHUB_API_TOKEN=your_token_here

Open terminal and write command: - 
uvicorn rag_service.app.main:app --reload
