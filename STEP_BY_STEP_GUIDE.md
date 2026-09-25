# 📘 Beginner-Friendly Step-by-Step Developer Guide

Welcome to the **Self-Correcting Code Review & Architectural Audit Agent**! 

This guide is designed for developers of all experience levels. Whether you are brand new to Python, AI agents, or static analysis, every single step is explained in clear, plain language with copy-pasteable commands.

---

## 🎯 What Does This Agent Do?

Imagine having a senior software engineer paired with a robot assistant:
1. **Reads Your Code**: It scans your Python files using **Tree-Sitter** to understand your functions, classes, and how they call each other.
2. **Runs Quality Tools**: It tests your code using **Ruff** (for syntax and style), **Mypy** (for type errors), and **Pytest** (to check if your tests pass).
3. **Automatically Fixes Bugs**: If an error is found, it sends the error and code to **Google Gemini 3.5 Flash-Lite (Free Tier)** to generate a code fix.
4. **Verifies in a Sandbox**: It tests the fix in an isolated sandbox. If tests still fail, it retries up to 3 times in a self-correcting loop.
5. **Applies the Patch**: Once all checks pass, it applies the fix to your file or posts a review on GitHub!

---

## 📋 Prerequisites

Before starting, ensure you have:
1. **Python 3.10 or higher** installed. Check in your terminal:
   ```bash
   python3 --version
   ```
2. **Git** installed:
   ```bash
   git --version
   ```

---

## 🚀 Step 1: Set Up the Environment

Open your terminal and navigate to the project directory:

```bash
cd "CodeReviewArchitecturalAgent"
```

### 1.1 Create a Python Virtual Environment
A virtual environment keeps the project's dependencies isolated from your computer's global packages:

```bash
python3 -m venv .venv
```

### 1.2 Activate the Virtual Environment
- **On macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```
- **On Windows (Command Prompt):**
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **On Windows (PowerShell):**
  ```powershell
  .venv\Scripts\Activate.ps1
  ```

*(You will know it worked when you see `(.venv)` at the beginning of your terminal prompt).*

---

## 📦 Step 2: Install Dependencies

Run this single command to install all necessary libraries:

```bash
pip install -r requirements.txt
```

### What gets installed?
- `google-genai`: The official SDK to call Google Gemini 3.5 Flash-Lite.
- `langgraph`: Orchestrates the self-correction retry loop and agent state machine.
- `qdrant-client`: The vector database for semantic code search.
- `tree-sitter` & `tree-sitter-python`: The engine that parses Python code into Abstract Syntax Trees (AST).
- `ruff`, `mypy`, `pytest`: Automated code quality tools and test runners.
- `fastapi` & `uvicorn`: Web framework for handling GitHub webhooks.

---

## 🔑 Step 3: Configure Environment Variables (.env)

The project includes an `.env.example` template. If you don't already have a `.env` file, copy it:

```bash
cp .env.example .env
```

Open `.env` in any text editor. It contains settings like this:

```ini
# Google Gemini API Settings (Free Tier)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_EMBEDDING_MODEL=gemini-embedding-001

# Qdrant Vector Store Configuration (Cloud Cluster)
QDRANT_URL=https://1522134f-8fad-4ebd-a8d6-bf98c9d93832.us-west-1-0.aws.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
QDRANT_COLLECTION_NAME=codebase_symbols

# Agent Loop & Sandbox Configuration
MAX_RETRIES=3
SANDBOX_TIMEOUT_SECONDS=30
REQUIRE_HUMAN_APPROVAL_FOR_STRUCTURAL_CHANGES=true
```

### How to get a Free Google Gemini API Key:
1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click **"Get API key"** and create a free key.
4. Paste it into `.env` next to `GEMINI_API_KEY=`.

> [!NOTE]
> **No API Key yet? No problem!** The agent includes a built-in deterministic heuristic engine. You can run tests, index code, and perform benchmark self-corrections completely offline without any API key.

---

## 🧪 Step 4: Run Your First Audit (Hands-On Tutorial)

The repository comes with a sample folder called `benchmark_sample/` that contains two files:
- `buggy_math.py`: An intentionally broken file with an unused import (`sys`) and a subtraction bug (`a - b` instead of `a + b`).
- `test_buggy_math.py`: A test suite expecting `calculate_sum(3, 4) == 7`.

Run the agent on this sample using the CLI:

```bash
python -m code_review_agent.cli audit --path benchmark_sample --auto-approve
```

### What You Will See:
1. **Ingestion**: It parses `buggy_math.py` and `test_buggy_math.py` into symbols.
2. **Analysis**:
   - `Ruff` catches the unused `sys` import (`F401`).
   - `Pytest` runs and fails with `assert -1 == 7`.
3. **Self-Correction**:
   - The agent invokes `gemini-3.5-flash-lite` (or the local fallback) to synthesize a patch.
   - It applies the fix inside the sandbox.
4. **Re-Testing**:
   - It re-runs the tests. Now all tests pass!
5. **Success Output**:
   ```
   ============================================================
   🏁 Audit Status: COMPLETE
   ============================================================
   ### 🚀 Self-Correction Successful
   - Applied and verified 1 patch(es).
   - All test suites passed after 1 iteration(s).

   Applied Patches: 1
     1. benchmark_sample/buggy_math.py - Fixed 2 issues on attempt 1.
   ```

Check `benchmark_sample/buggy_math.py`—you will see that the unused import was removed and `return a - b` was fixed to `return a + b`!

---

## 🔍 Step 5: Inspect Code Symbols and Chunks

Want to see how Tree-Sitter and the AST parser analyze code? Run the `index` command:

```bash
python -m code_review_agent.cli index --path benchmark_sample
```

**Output:**
```
Indexing AST symbols in: benchmark_sample
Found 4 logical code chunks:
  [FUNCTION] calculate_sum (buggy_math.py:4-7)
  [FUNCTION] multiply_numbers (buggy_math.py:10-12)
  [FUNCTION] test_calculate_sum (test_buggy_math.py:4-5)
  [FUNCTION] test_multiply_numbers (test_buggy_math.py:8-9)
```

Unlike basic chunkers that blindly cut files every 500 words, this chunker keeps entire functions and classes intact, preserving context for the AI.

---

## 🚦 Step 6: Run the Complete Automated Test Suite

To verify that all components (AST parser, error parser, sandbox rollback, and LangGraph workflow) work properly on your machine:

```bash
pytest tests/ -v
```

All 8 tests will run and pass:
```
tests/test_ast_parser.py::test_ast_parsing_symbols PASSED                [ 12%]
tests/test_ast_parser.py::test_code_chunker_logical_units PASSED         [ 25%]
tests/test_error_parser.py::test_parse_ruff_output PASSED                [ 37%]
tests/test_error_parser.py::test_parse_mypy_output PASSED                [ 50%]
tests/test_error_parser.py::test_parse_pytest_output PASSED              [ 62%]
tests/test_sandbox.py::test_sandbox_run_command PASSED                   [ 75%]
tests/test_sandbox.py::test_sandbox_snapshot_and_rollback PASSED         [ 87%]
tests/test_self_correction_graph.py::test_self_correcting_audit_workflow PASSED [100%]
```

---

## 🛠️ Step 7: Auditing Your Own Custom Projects

You can use this tool on any Python project on your computer:

### Audit an Entire Project Folder:
```bash
python -m code_review_agent.cli audit --path /path/to/your/project
```

### Audit Specific Files:
```bash
python -m code_review_agent.cli audit --path /path/to/your/project --files main.py utils.py
```

### Human-in-the-Loop Mode vs Auto-Approve:
- By default, if the AI proposes a **structural change** (e.g. deleting a function or modifying a public class interface), the agent pauses and asks for human confirmation.
- If you want the agent to automatically apply all verified fixes without waiting, add `--auto-approve`:
  ```bash
  python -m code_review_agent.cli audit --path . --auto-approve
  ```

---

## 🌐 Step 8: GitHub Integration (No Token Needed!)

You never need to copy-paste or expose Personal Access Tokens to use this agent with GitHub:

### Option A: Automatic GitHub CLI Detection
If you have the official GitHub CLI (`gh`) installed and have already run `gh auth login`, the agent **automatically detects your active session token**. You do not need to set `GITHUB_TOKEN` in `.env`.

### Option B: Native GitHub Actions (Recommended)
This repository includes [`.github/workflows/code_review.yml`](file:///.github/workflows/code_review.yml).
When you push this repository to GitHub:
1. Every time someone opens a Pull Request, GitHub Actions triggers automatically.
2. GitHub automatically provides a temporary, safe `${{ secrets.GITHUB_TOKEN }}`.
3. The agent reviews the PR, runs the tests, and reports back—with zero setup!

### Option C: GitHub Webhook Server
If you want to run your own self-hosted webhook server to receive GitHub events:
```bash
python -m code_review_agent.cli serve --port 8000
```
This starts a high-performance **FastAPI** server that listens for incoming `pull_request` and `push` events at `http://your-server:8000/webhook`.

---

## 🛡️ Safety & Sandbox Protection

What if the AI generates bad code that crashes?
- **Automatic Snapshotting**: Before applying any fix, the agent takes a snapshot of your original files in memory.
- **Rollback Guarantee**: If tests fail and the agent cannot resolve them within 3 attempts, it **automatically rolls back** all files to their pristine original state. Your code will never be left in a broken state.
- **Timeout Protection**: Analyzers and test suites are limited to 30 seconds by default (configurable via `SANDBOX_TIMEOUT_SECONDS`), preventing runaway infinite loops.

---

## ❓ Frequently Asked Questions (FAQ)

**Q: Do I have to pay anything to run this?**  
**A:** No! It is specifically engineered to use Google Gemini's **Free Tier** (`gemini-3.5-flash-lite`).

**Q: What if I run out of API rate limits on Gemini Free Tier?**  
**A:** The agent has built-in **exponential backoff**. If a rate limit (HTTP 429) occurs, it automatically pauses, waits, and retries.

**Q: Can this run on Windows, Mac, and Linux?**  
**A:** Yes! The path resolution, subprocess sandbox, and Tree-Sitter parsers are cross-platform.

**Q: How do I change the maximum number of self-correction retries?**  
**A:** In your `.env` file, change `MAX_RETRIES=3` to any integer you prefer (e.g. `MAX_RETRIES=5`).
