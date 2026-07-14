# Autonomous Code Reviewer AI (AI Engineering Internship Edition)

A production-ready, modular Agentic AI system that ingests repositories, parses syntax structure, executes target inspection agents (using Claude 3.5 Sonnet), runs a retrieval-augmented generation (RAG) loop over structural code conventions, and exposes capabilities natively via a FastAPI gateway and a Model Context Protocol (MCP) server integration.

---

## Key AI Engineering Paradigms

1. **Modular Agentic Pipeline**: Instead of running a single monolithic LLM prompt, the system routes tasks through a sequence of dedicated domain-specific agents (Language Detection, Parsing, Review, Security, Improvements, and Documentation) orchestration in a pipeline.
2. **RAG-Enabled Analysis (LangChain + ChromaDB)**: Code chunks are vectorized and indexed into a local ChromaDB store. The RAG Engine acts as a semantic memory, pulling down coding style guidelines, library docs, or security patterns to augment the LLM context.
3. **Model Context Protocol (MCP) Ready**: Built-in support for MCP. The system operates both as a traditional HTTP REST API and as an MCP Server. This allows client IDEs (e.g., Cursor, Claude Desktop, VSCode extensions) to natively leverage the reviewer's agents.
4. **Clean Architecture & SOLID Design**: Clear separation between Domain entities, Use Case interactors (Ports/SPIs), and Infrastructure layers (Adapters like LangChain, ChromaDB, Claude Client, database ORM).

---

## Folder Structure

```text
backend/
├── app/
│   ├── core/                  # Configuration & logging initialization
│   ├── domain/                # Enterprise entities (Analysis, Issue, Diff, Report)
│   ├── use_cases/             # Orchestrator & Port interfaces (db, llm, rag, mcp)
│   ├── infrastructure/        # Framework implementations (Adapters)
│   │   ├── api/               # FastAPI controllers & JSON schemas
│   │   ├── database/          # PostgreSQL SQLAlchemy DB repository
│   │   ├── repository_loader/ # Code source loader (Git / ZIP)
│   │   ├── language_detector/ # Code language categorization
│   │   ├── code_parser/       # Syntactic parsing (AST / Tree-Sitter)
│   │   ├── llm/               # Claude API client wrapper & Prompt Library
│   │   ├── agents/            # Review, Security, Improvement, Doc agents
│   │   ├── rag/               # LangChain + ChromaDB implementation
│   │   ├── mcp/               # Model Context Protocol server/adapter
│   │   └── report/            # PDF and HTML formatting output
│   └── worker/                # Celery & Redis background workers
```

---

## Environment Configuration

Update your `.env` (copied from `.env.example`) with the required keys:

- **LLM Engine**: `ANTHROPIC_API_KEY` (Claude 3.5 Sonnet).
- **RAG Store**: `VECTOR_DB_DIR` and `CHROMA_HOST` to connect to the database.
- **MCP Server**: `MCP_PORT` (defaults to 8500) to expose Model Context Protocol hooks.
- **LLM Observability**: We configure LangChain / LangSmith tracing settings to monitor token usage, latency, and prompt traces (vital for internship profiling).

---

## Getting Started

### 1. Build and Run the Complete Stack
Utilize docker-compose to launch PostgreSQL, Redis, ChromaDB, the FastAPI API and MCP endpoint, and the Celery background worker:

```bash
docker-compose up --build
```

### 2. Standard FastAPI Endpoint
The Swagger UI API docs will be available at:
`http://localhost:8000/docs`

### 3. Model Context Protocol (MCP) Interface
The system listens for MCP JSON-RPC connections at:
`http://localhost:8500`

Clients can bind the MCP server directly to call tools such as:
- `analyze_repository(git_url: str)`
- `query_rag_codebase(query: str)`
- `generate_improvement_patch(issue_id: str)`
