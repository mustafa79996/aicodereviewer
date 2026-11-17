# ⚡ AI Code Review & Bug Detection System

> **A Next-Generation Intelligent Code Review and Automated Bug Detection Platform**  
> *Combines Advanced Static Code Analysis (SAST) with AI / LLM Reasoning, Code Quality Metrics, and Automated Fix Generation.*  
> *Entire project, virtual environment, and database reside strictly on `D:\ai-code-reviewer`.*

---

## 📌 Executive Summary

Traditional code review is manual, slow, and frequently overlooks subtle bugs, security vulnerabilities, or performance bottlenecks. The **AI Code Review and Bug Detection System** automates the entire review lifecycle:
1. **Detects** syntax errors, logical bugs, security vulnerabilities (OWASP Top 10), coding standard violations, and performance anti-patterns.
2. **Quantifies** code health with Cyclomatic Complexity, Maintainability Index (MI), Halstead Software Metrics, and an overall Quality Score (0–100%) with letter grades (A+ to F).
3. **Explains** issues in clear developer-friendly language with exact line numbers and code snippets.
4. **Fixes** detected issues automatically by generating refactored code and an interactive unified diff patch.
5. **Persists** review audits and metrics in a local SQLite database for history tracking and codebase analytics.

---

## 🏗️ Architecture & Dual-Engine Pipeline

```
  [User Source Code] ───► (Upload or Code Studio Input)
                                    │
                                    ▼
                     ┌───────────────────────────────┐
                     │       Review Orchestrator     │
                     └──────────────┬────────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌─────────────────────────────────┐        ┌───────────────────────────────────┐
│     Static Code Analyzers       │        │         AI / LLM Engine           │
│  - Python AST & Tokenizer       │        │  - Built-in Semantic Analyzer     │
│  - JavaScript / TypeScript      │        │  - Google Gemini API              │
│  - Java SAST Rules              │        │  - OpenAI GPT-4o / GPT-4o-mini    │
│  - C / C++ Memory & Buffer      │        │  - Ollama (Local Offline LLM)     │
│  - Go Concurrency & Error Hand. │        │  - Groq Llama 3                   │
│  - SQL Safety & Performance     │        └─────────────────┬─────────────────┘
│  - Universal Security / Secrets │                          │
└────────────────┬────────────────┘                          │
                 │                                           │
                 └──────────────────┬────────────────────────┘
                                    ▼
                ┌───────────────────────────────────────┐
                │        Metrics & Scoring Engine       │
                │  - Cyclomatic & Cognitive Complexity  │
                │  - Maintainability Index (MI)         │
                │  - Halstead Software Science          │
                │  - Quality Scorecard (0-100%, Grade)  │
                └───────────────────┬───────────────────┘
                                    ▼
                ┌───────────────────────────────────────┐
                │       Automated Correction & Diff     │
                │  - Heuristic & AI Refactoring Engine  │
                │  - Unified Patch Diff (Git format)    │
                └───────────────────┬───────────────────┘
                                    ▼
                ┌───────────────────────────────────────┐
                │   Web Dashboard & SQLite History DB   │
                │  - Side-by-side Diff Viewer           │
                │  - Filterable Issue Diagnostics       │
                │  - Markdown & JSON Audit Export       │
                └───────────────────────────────────────┘
```

---

## 🚀 Key Features

### 1. Multi-Language Code Analysis
- **Python**: AST syntax parsing, SQL injection detection, command injection (`os.system`, `subprocess`), mutable default arguments, resource leaks (`open()` without `with`), swallowed exceptions (`except: pass`), built-in shadowing, weak hashing (`MD5`/`SHA-1`), pickle deserialization.
- **JavaScript / TypeScript**: Unmatched brackets/syntax, `eval()` and dynamic code execution, DOM XSS (`innerHTML`, `document.write`), loose equality (`==` vs `===`), legacy `var` declarations, empty catch blocks, prototype pollution.
- **Java**: String comparison via `==`, NullPointerException risks (`var.equals("const")`), SQL injection in `Statement.executeQuery()`, unclosed streams/resources, weak crypto (DES/MD5), empty catch blocks.
- **C / C++**: Deprecated unsafe functions (`gets`, `strcpy`, `strcat`, `sprintf`), format string vulnerabilities in `printf`, dynamic memory leaks (`malloc` without `free`, `new` without `delete`), raw pointer allocation.
- **Go**: Ignored error returns (`_, _ = ...`), goroutine leaks without context cancellation, panic anti-patterns.
- **SQL**: Destructive `DELETE` or `UPDATE` queries without `WHERE` clauses, wildcard `SELECT *` anti-patterns, non-sargable leading wildcard `LIKE '%query'`.
- **Universal / Cross-Language**: Detection of hardcoded AWS credentials, GitHub tokens, Slack tokens, Stripe keys, private RSA/SSH keys, plaintext passwords, insecure HTTP URLs, deep nesting (> 4 levels).

### 2. Multi-Provider AI Support
- **Built-in Smart Engine (Default)**: 100% offline rule and semantic reasoning engine. Runs with zero external API dependencies.
- **Google Gemini**: Deep architectural critiques and refactoring via `gemini-1.5-pro` or `gemini-1.5-flash`.
- **OpenAI**: Semantic review and code rewriting via `gpt-4o` or `gpt-4o-mini`.
- **Ollama**: Offline local LLMs (e.g. `codellama`, `deepseek-coder`, `llama3`).
- **Groq**: Ultra-fast inference using Llama 3 models.

### 3. Automated Code Correction & Interactive Diff
- Automatic generation of clean, corrected code fixing all identified vulnerabilities.
- Side-by-side and unified git diff showing added and removed lines.
- 1-click **"Apply to Editor"**, **"Copy"**, or **"Download Fixed File"**.

### 4. Code Quality Metrics & Scoring
- **Overall Quality Score (0–100%)** with letter grade (`A+`, `A`, `B`, `C`, `D`, `F`).
- **Sub-Scores**: Security (0–100%), Reliability (0–100%), Maintainability (0–100%), Performance (0–100%).
- **Cyclomatic & Cognitive Complexity**.
- **Maintainability Index (MI)** (scaled to 100).
- **Halstead Software Science Metrics** (Volume, Difficulty, Estimated Bug Count).
- **SLOC, LLOC, Blank Lines, Comment Lines, Comment-to-Code Ratio**.

### 5. Persistent History & Analytics
- SQLite database on `D:\ai-code-reviewer\data\reviews.db`.
- History drawer with one-click reload of past reviews.
- Analytics dashboard tracking total audits, average quality scores, and critical flaws prevented.
- One-click export of full audit reports in **Markdown format**.

---

## 📂 Project Directory Structure

```
D:\ai-code-reviewer\
├── .cache\                  # Pip and execution cache (strictly on D:)
├── data\                    # SQLite database (reviews.db)
├── venv\                    # Python virtual environment (Python 3.14)
├── app\
│   ├── config.py            # Global paths and defaults
│   ├── models.py            # Pydantic data schemas
│   ├── database.py          # SQLite database storage & queries
│   ├── main.py              # FastAPI server & REST API
│   ├── engine\
│   │   ├── orchestrator.py  # Coordinates static analysis, AI, and metrics
│   │   ├── metrics.py       # Complexity, Halstead, MI, and Quality scoring
│   │   ├── fixer.py         # Heuristic auto-fixer and diff generator
│   │   ├── ai_engine.py     # Gemini, OpenAI, Ollama, Groq, and built-in AI
│   │   └── analyzers\       # Specialized static code analyzers
│   │       ├── base.py
│   │       ├── python_analyzer.py
│   │       ├── javascript_analyzer.py
│   │       ├── java_analyzer.py
│   │       ├── cpp_analyzer.py
│   │       ├── go_analyzer.py
│   │       ├── sql_analyzer.py
│   │       └── universal_analyzer.py
│   ├── static\
│   │   ├── css\app.css      # Dark theme & styling
│   │   ├── js\app.js        # Dynamic UI interaction & API calls
│   │   └── samples\         # Pre-loaded bug-ridden sample codes
│   └── templates\
│       └── index.html       # Single Page Application Dashboard
├── tests\                   # Automated pytest suite (16 tests)
│   ├── test_analyzers.py
│   ├── test_metrics.py
│   ├── test_fixer.py
│   └── test_api.py
├── start.bat                # Windows Batch launcher
├── start.ps1                # PowerShell launcher
├── run_server.py            # Python server runner
├── requirements.txt         # Dependency specification
└── README.md                # System documentation
```

---

## ⚡ Quick Start Instructions

### Running the System
Double-click `start.bat` or run in PowerShell:
```powershell
Set-Location -Path "D:\ai-code-reviewer"
.\start.ps1
```
Or directly using Python:
```powershell
$env:PYTHONPATH = "D:\ai-code-reviewer"
& "D:\ai-code-reviewer\venv\Scripts\python.exe" "D:\ai-code-reviewer\run_server.py"
```

Open your browser at:
👉 **`http://localhost:8000`**

### Running the Test Suite
```powershell
$env:PYTHONPATH = "D:\ai-code-reviewer"
& "D:\ai-code-reviewer\venv\Scripts\python.exe" -m pytest "D:\ai-code-reviewer\tests" -v
```

---

## 📡 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the web cockpit dashboard |
| `POST` | `/api/review` | Analyzes submitted code string and returns full review response |
| `POST` | `/api/upload` | Uploads code file (`.py`, `.js`, `.java`, `.cpp`, `.go`, `.sql`, etc.) |
| `GET` | `/api/samples` | Retrieves pre-configured bug-ridden code samples |
| `GET` | `/api/history` | Lists past reviews and quality scores |
| `GET` | `/api/history/{id}` | Retrieves full audit details for a specific review |
| `DELETE` | `/api/history/{id}` | Deletes a review record from SQLite database |
| `GET` | `/api/analytics` | Aggregates reviews, avg scores, bug counts, and languages |
| `GET` | `/api/export/{id}/markdown` | Downloads full audit report formatted in Markdown |
| `GET` | `/health` | Service health status check |
