# 📘 Beginner-Friendly Step-by-Step Developer Guide

Welcome to the **Self-Correcting Code Review & Architectural Audit Agent**! 

This guide is designed for developers of all experience levels. Whether you are brand new to Python, AI agents, or static analysis, every single step is explained in clear, plain language with copy-pasteable commands.

---

## 🎯 What Does This Agent Do?

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
- `pinecone`: The serverless vector database for semantic code search (does not pause after inactivity).
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

# Pinecone Vector Store Configuration (Serverless)
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=codebase-symbols
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# Agent Loop & Sandbox Configuration
MAX_RETRIES=3
SANDBOX_TIMEOUT_SECONDS=30
REQUIRE_HUMAN_APPROVAL_FOR_STRUCTURAL_CHANGES=true
```

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

## 🌲 Step 8: Setting Up Pinecone Vector Store

Why Pinecone over Qdrant?
- **No 1-Week Inactivity Pause**: Qdrant Cloud Free Tier automatically suspends your cluster after 7 days of inactivity. Pinecone's **Serverless Starter Tier (Free)** does **not** pause, keeping your vector index ready permanently.
- **Serverless Scaling**: Handles up to 100k vectors and 2GB storage completely free.

### 8.1 Get Your Free Pinecone API Key (Takes 2 Minutes)
1. Go to [Pinecone Console](https://app.pinecone.io/) and sign up / log in with GitHub or Google.
2. In the left navigation, click **API Keys**.
3. Copy your API Key (e.g., `pcsk_...`).

### 8.2 Add Pinecone to Your `.env` File
Open your `.env` file and set:
```ini
PINECONE_API_KEY=pcsk_your_actual_pinecone_api_key_here
PINECONE_INDEX_NAME=codebase-symbols
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
```

> [!TIP]
> **Don't want to sign up for Pinecone right now?**  
> Leave `PINECONE_API_KEY=` blank! The agent will automatically detect that no key is provided and use a **built-in transient in-memory vector store**. Everything will work out-of-the-box without errors.

---

## ⚡ Step 9: Preserving Free AI Quotas & Running GitHub Actions

If you are using **Google Gemini Free Tier**, running the agent automatically on every single `git push` will rapidly burn through your rate limits (15 RPM / 1,500 RPD) and cause `429 RESOURCE_EXHAUSTED` errors.

### 9.1 Recommended Approach: Run Locally via CLI
Running locally on your computer gives you 100% control:
```bash
# Audit specific files you just edited (uses the least tokens):
python -m code_review_agent.cli audit --files my_feature.py

# Or audit the entire workspace when ready:
python -m code_review_agent.cli audit --path .
```
- **0 GitHub Action minutes used**.
- **0 unexpected token burns** on minor edits or typo fixes.

### 9.2 Running On-Demand in GitHub Actions (`workflow_dispatch`)
The workflow in `.github/workflows/code_review.yml` is configured with **manual triggers**:
1. Push your code to GitHub.
2. Go to your repository on GitHub.com.
3. Click on the **Actions** tab at the top.
4. Select **"Self-Correcting Architectural Code Review"** from the left sidebar.
5. Click the **"Run workflow"** button on the right and select the branch.
6. The action runs only when requested, saving your AI quotas!

### 9.3 Fixing the "400 INVALID_ARGUMENT: API key not valid" Error
If you see the error:
`Error during Gemini fix synthesis: 400 INVALID_ARGUMENT. API key not valid`
This means GitHub Actions cannot find a valid Gemini key. Fix it in 3 steps:
1. Go to your GitHub repository: **Settings ➔ Secrets and variables ➔ Actions**.
2. Click **"New repository secret"**:
   - Name: `GEMINI_API_KEY`
   - Value: Paste your key from [Google AI Studio](https://aistudio.google.com/)
3. (Optional) Add `PINECONE_API_KEY` as another secret if you want persistent cloud vector storage in CI.

---

## 🛡️ Safety & Sandbox Protection

What if the AI generates bad code that crashes?
- **Automatic Snapshotting**: Before applying any fix, the agent takes a snapshot of your original files in memory.
- **Rollback Guarantee**: If tests fail and the agent cannot resolve them within 3 attempts, it **automatically rolls back** all files to their pristine original state. Your code will never be left in a broken state.
- **Timeout Protection**: Analyzers and test suites are limited to 30 seconds by default (configurable via `SANDBOX_TIMEOUT_SECONDS`), preventing runaway infinite loops.

---

## ❓ Frequently Asked Questions (FAQ)

**Q: Do I need GitHub Actions to run automatically?**  
**A:** No! Running automatically on every push is strongly discouraged on the free AI tier because it burns daily quotas on minor commits. Run locally or use the manual "Run workflow" button instead.

**Q: Why did Qdrant stop working after 1 week?**  
**A:** Qdrant Cloud pauses free clusters after 7 days of inactivity. The project now uses **Pinecone Serverless**, which does not pause after inactivity, or the built-in in-memory fallback.

**Q: Do I have to pay anything to run this?**  
**A:** No! It is specifically engineered to use Google Gemini's **Free Tier** (`gemini-3.5-flash-lite`) and Pinecone's **Free Starter Tier**.

**Q: What if I run out of API rate limits on Gemini Free Tier?**  
**A:** The agent has built-in **exponential backoff**. If a rate limit (HTTP 429) occurs, it automatically pauses, waits, and retries. If no key is set or quota is exhausted, it applies rule-based heuristic fixes.

**Q: How do I change the maximum number of self-correction retries?**  
**A:** In your `.env` file, change `MAX_RETRIES=3` to any integer you prefer (e.g. `MAX_RETRIES=5`).
