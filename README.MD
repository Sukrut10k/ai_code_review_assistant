# AI Code Review Assistant

An end-to-end **AI-powered code review assistant** built as part of the Unthinkable Solutions assignment.

The app lets developers:

- Upload one or more source files
- Run an AI-driven review (LLM + light static analysis)
- Get a structured report with:
  - Summary & detailed feedback
  - Issues tagged by **severity** and **category**
  - **Auto-fix suggestions** with code patches
  - **Code quality score (1–10)**
  - File-level **metrics** (lines, comments, complexity)
  - Highlighted **security red flags**
- Save every review to **MySQL**
- View history & download each report as a **PDF**

---

## Key Features

### 1. Multi-language Code Upload
- Supports: `Python`, `JavaScript`, `Java`, `C`, `C++`, `Go`, `PHP`, `SQL`, `HTML`, `CSS`, `Bash`, and generic text via `.txt`. :contentReference[oaicite:6]{index=6}  
- Automatic language detection based on file extension.

### 2. Hybrid Analysis (LLM + Static Signals)
- Uses **Groq Llama 3.1** via API for deep semantic review:
  - Readability & clarity
  - Modularity & design
  - Bugs & edge cases
  - Security & performance
  - Testing & best practices  
- Local pre-processing:
  - Line counts, code vs comments, complexity score per file
  - Simple regex-based **security scan** (SQL injection patterns, hard-coded secrets, `eval/exec`, shell injection etc.)

### 3. Structured Issue Model
Each detected issue includes: :contentReference[oaicite:9]{index=9}  

- `severity`: `critical | high | medium | low | info`
- `category`: `bug | security | performance | readability | style | test | other`
- `file`, `line_start`, `line_end`
- `message` (what’s wrong)
- `suggestion` (how to fix)
- `code_patch` (optional auto-fix snippet)

### 4. Code Quality Dashboard (Streamlit UI)
The **Upload Code** page shows 

- Overall **quality score** (1–10)
- Total issues + count of critical issues
- Total lines of code across files
- File metrics (per file):
  - total lines
  - code lines
  - comment ratio %
  - simple complexity score
- “Code strengths” – list of good practices the LLM found
- Issues grouped by severity, each with suggestion + optional patch
- One-click **PDF export** of the full review

### 5. Persistent Storage (MySQL)

All reviews are stored in a MySQL `reviews` table with:

- `id`, `created_at`
- `filenames`
- `summary`, `details`, `raw_response`
- `issues_json` – structured issues
- `quality_score` – numeric rating
- `metrics_json` – per-file metrics
- `strengths_json` – positive findings

Extra helper SQL scripts live in `db_scripts/demo_queries.sql` (view all reviews, count, reset, etc.). 

### 6. REST API (FastAPI)

FastAPI backend exposes:  

- `GET /health` – simple health check  
- `POST /api/review` – upload 1–N files, trigger analysis, save & return review  
- `GET /api/reports?limit=N` – list recent reviews (for history view)  
- `GET /api/reports/{id}` – fetch full details of a specific review  

Interactive docs: `http://127.0.0.1:8000/docs`

### 7. Review History & PDF Download

The **Review History** page in Streamlit: 

- Lists recent reviews (from MySQL) with summary and quality score
- Lets you select a review and:
  - View full detailed feedback
  - See issues grouped by severity
  - Download the report as a nicely formatted **PDF**

---

## Tech Stack

- **Backend**: Python, FastAPI  
- **Frontend**: Streamlit 
- **Database**: MySQL (via `mysql-connector-python`)
- **LLM**: Groq API – `llama-3.1-8b-instant`
- **Other**: `python-dotenv`, `requests`, `fpdf2` (PDF export)

---

## Project Structure

```text
code_review_assistant/
├── backend/
│   ├── db.py              # MySQL connection, schema, insert/fetch helpers
│   ├── llm_service.py     # Metrics, security scan, Groq LLM integration
│   ├── main.py            # FastAPI app & endpoints
│   └── schemas.py         # Pydantic models for API responses
├── frontend/
│   ├── app.py             # Streamlit UI & dashboard
│   └── fonts/
│       └── DejaVuSans.ttf # Unicode-safe font for PDF export
├── db_scripts/
│   └── demo_queries.sql   # Handy SQL queries (view/reset reviews)
├── tests/                 # Sample test files used in demo
├── .env                   # Environment variables (not committed)
├── requirements.txt
└── README.md
````

---

## Setup & Installation

> Prerequisites:
> – Python 3.10+
> – MySQL server running locally
> – A Groq API key (for LLM calls)

### Clone the repository

```bash
git clone https://github.com/Sukrut10k/ai_code_review_assistant.git
cd ai_code_review_assistant
```

### Create and activate virtual environment

```bash
python -m venv venv
venv\Scripts\activate      # On Windows
# source venv/bin/activate # On Linux/macOS
```

### Install dependencies

Direct way (as you used while developing):

```bash
pip install fastapi uvicorn streamlit mysql-connector-python python-dotenv requests
pip install python-multipart
pip install fpdf2
pip freeze > requirements.txt (To generate requirements.txt)
```
---

## Environment Variables (.env)

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
AI_MODEL=llama-3.1-8b-instant

DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=code_review_db
```

> **Do not commit `.env`** – keep your keys and passwords private.

---

## Database Setup

The backend automatically:

* Creates the database `code_review_db` (if missing)
* Creates the `reviews` table
* Adds columns for `issues_json`, `quality_score`, `metrics_json`, `strengths_json` 

You just need MySQL running and correct credentials in `.env`.

Optionally, you can run helper queries from:

```bash
# From MySQL client / Workbench:
SOURCE db_scripts/demo_queries.sql;
```

---

## Running the Application

### Start the FastAPI backend

From the project root:

```bash
uvicorn backend.main:app --reload
```

FastAPI will be available at:

* API base: `http://127.0.0.1:8000`
* Swagger UI: `http://127.0.0.1:8000/docs#/`

You can test `/api/review` directly from Swagger by uploading a file.

### Start the Streamlit frontend

In a **second terminal**, with the same virtual environment:

```bash
streamlit run frontend/app.py
```

Open in browser:

```text
http://localhost:8501
```

### Typical Usage Flow

1. Go to **Upload Code**
2. Upload one or more source files
3. Click **Analyze Code**
4. View:

   * Quality score
   * Metrics and strengths
   * Summary & detailed review
   * Issues grouped by severity
5. Click **Download PDF report** (optional)
6. Go to **Review History** to browse previous reviews

---

## API Quick Reference

### `POST /api/review`

* **Description**: Analyze uploaded code files and store the review.
* **Request**: `multipart/form-data` with one or more `files`
* **Response** (`ReviewResponse`): 

```json
{
  "id": 1,
  "summary": "...",
  "details": "...",
  "issues": [ { "severity": "high", "category": "bug", ... } ],
  "raw_response": "...",
  "quality_score": 7.8,
  "strengths": ["Good use of functions", "..."],
  "metrics": {
    "file.py": {
      "total_lines": 42,
      "code_lines": 30,
      "comment_lines": 5,
      "complexity_score": 8,
      "comment_ratio": 11.9
    }
  }
}
```

### `GET /api/reports?limit=10`

Returns a list of recent reviews (id, filenames, summary, quality_score). 

### `GET /api/reports/{id}`

Returns full review details, including issues, strengths, metrics, and raw LLM response. 

---

## Sample Test Files

The `tests/` folder contains small Python/JS/HTML/Java files to demonstrate: 

* Clean code vs issues
* Security pitfalls like XSS
* Performance & readability problems

These are ideal for demo recordings.

---

## Possible Future Improvements

* User authentication & multi-tenant workspaces
* Per-project dashboards & trends over time
* Inline diff view for patches
* CI/CD integration (GitHub Actions hook)
* More advanced static analysis per language

---