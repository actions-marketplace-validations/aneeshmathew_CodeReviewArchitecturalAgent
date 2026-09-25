# Self-Correcting Code Review & Architectural Audit Agent
**Scope & Architecture Specification Document**

---

## 1. Executive Summary & Goals
The Self-Correcting Code Review & Architectural Audit Agent is an developer tool that integrates with GitHub repositories. It performs automated codebase indexing, static analysis tool execution, architectural health evaluation, and self-correcting pull request (PR) generation.

### Primary Portfolio Objectives
- **Demonstrate Self-Correction & Loop Control:** Automated code generation -> test execution -> error analysis -> retry graph loop.
- **Showcase Tree-Sitter & Code RAG:** Structural code parsing combined with semantic vector search.
- **Implement Human-in-the-Loop Safeguards:** Intercept critical structural changes for manual approval before posting PRs.

---

## 2. System Architecture & Component Design

```
                      +---------------------------------------+
                      |         GitHub Event Webhook          |
                      |       (PR Opened / Push Event)        |
                      +-------------------|-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |          FastAPI Worker Engine        |
                      +-------------------|-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |     LangGraph Orchestrator Graph      |
                      +---|-----------------|--------------|--+
                          |                 |              |
     +--------------------+                 |              +--------------------+
     v                                      v                                   v
+------------------------+     +------------------------+     +------------------------+
| Code Base Ingestion    |     |  Static Analysis Tool  |     |  Self-Correction Engine|
| (Tree-Sitter + Vector) |     |  (Ruff, Pytest, Mypy)  |     |  (Fix Code & Re-Test)  |
+-----------|------------+     +-----------|------------+     +-----------|------------+
            |                              |                              |
            v                              v                              v
+------------------------+     +------------------------+     +------------------------+
| Semantic Code Store    |     |  Execution Sandbox     |     |  Human Approval Node   |
| (Qdrant Code Vectors)  |     |   (Isolated Docker)    |     | (Post GitHub Comments) |
+------------------------+     +------------------------+     +------------------------+
```

---

## 3. Technology Stack & Key Libraries

| Domain | Technology / Library | Purpose |
| :--- | :--- | :--- |
| **Code Parsing** | `tree-sitter` / `ast` (Python) | Structural parsing of ASTs to extract functions, classes, and call graphs |
| **Agent Framework** | LangGraph | Stateful self-correction execution loops |
| **Static Analyzers**| Ruff, Mypy, Pytest | Automated verification tools |
| **Vector Indexing** | Qdrant / Pinecone + CodeBERT or OpenAI Embeddings | Semantic code search and impact analysis |
| **Sandbox Execution**| Docker Container Engine / Subprocess Sandbox | Safe execution of test suites against LLM-generated code fixes |
| **Integration** | PyGithub / GitHub REST API | Automated PR generation, inline line-item comment additions |

---

## 4. Graph Architecture & Self-Correction Logic

```
   [Inbound PR Event] 
           │
           ▼
  [Index Repo & AST]
           │
           ▼
[Run Static Analyzers (Ruff/Mypy)]
           │
           ├── Errors Detected? ─── NO ──► [Generate LGTM Summary] ──► [Post Comment]
           │
          YES
           │
           ▼
 [Synthesize Fix (LLM)]
           │
           ▼
 [Run Test Suite in Docker]
           │
           ├── Tests Passed? ───── YES ─► [Human-in-the-Loop Check] ─► [Create GitHub PR]
           │
          NO (Retry Count < 3)
           │
           └───────────────────────────────────┘
```

### State Schema (`AuditState`)
```python
from typing import TypedDict, List, Dict, Any, Optional

class AuditState(TypedDict):
    repo_url: str
    commit_sha: str
    changed_files: List[str]
    ast_summary: Dict[str, Any]
    static_errors: List[Dict[str, Any]]
    suggested_patches: List[Dict[str, str]]
    test_results: Dict[str, Any]
    retry_count: int
    is_approved_by_human: bool
```

---

## 5. Implementation Milestones

### Phase 1: AST Parsing & Code Indexing Engine (Days 1–3)
- Set up `tree-sitter` parser to traverse repository files and extract symbols, function definitions, and dependency trees.
- Chunk codebase by logical units (functions/classes) rather than fixed token length.
- Index symbols into vector database with metadata tags.

### Phase 2: Static Analysis & Docker Execution Sandbox (Days 4–6)
- Build isolated execution environment running Python linters (`ruff`, `mypy`) and test execution (`pytest`).
- Structured error parser to transform raw terminal output into JSON diagnostic inputs for the LLM.

### Phase 3: LangGraph Self-Correction Loop (Days 7–10)
- Implement state machine with retry nodes.
- Define patch generator prompt taking AST context + stack trace output.
- Set up loop termination condition (`max_retries = 3` or `tests_passed == True`).

### Phase 4: GitHub API Integration & Human-in-the-Loop (Days 11–13)
- Create webhook handler in FastAPI listening for `pull_request.opened` events.
- Implement inline comment publisher via PyGithub.
- Add human approval check before pushing auto-correction code commits.

### Phase 5: Documentation & Benchmark Suite (Days 14–15)
- Test agent against intentionally buggy sample repos (e.g., benchmark suite with syntax errors, type bugs, failing unit tests).
- Measure patch resolution success rate.
- Document system architecture with diagrams in portfolio README.