import json
from typing import List, Dict

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import ReviewResponse, ReviewListItem, ReviewDetail, Issue
from .llm_service import review_code_with_llm, LLMConfigError
from .db import init_db, insert_review, fetch_recent_reviews, fetch_review_by_id


app = FastAPI(
    title="AI Code Review Assistant",
    description="Backend API for automated code review using Groq LLM.",
    version="0.4.0",
)

# CORS so Streamlit (on another port) can call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """
    Initialize the database when the FastAPI app starts.
    """
    init_db()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/review", response_model=ReviewResponse)
async def review_code(files: List[UploadFile] = File(...)):
    """
    Accept one or more code files, send them to the LLM, store the result in DB,
    and return the saved review (with ID and structured issues).
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    file_contents: Dict[str, str] = {}
    filenames: List[str] = []

    max_files = 10

    if len(files) > max_files:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files uploaded. Maximum allowed is {max_files}.",
        )

    for upload in files:
        try:
            content_bytes = await upload.read()
            if len(content_bytes) > 1_000_000:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {upload.filename} is too large (max 1MB for demo).",
                )

            content_str = content_bytes.decode("utf-8", errors="ignore")
            file_contents[upload.filename] = content_str
            filenames.append(upload.filename)

        finally:
            await upload.close()

    # Call LLM service
    try:
        llm_result = review_code_with_llm(file_contents)
    except LLMConfigError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    summary = llm_result.get("summary", "").strip()
    details = llm_result.get("details", "").strip()
    raw_response = llm_result.get("raw_response", "").strip()
    issues = llm_result.get("issues", []) or []
    quality_score = llm_result.get("quality_score", 5.0)
    strengths = llm_result.get("strengths", [])
    metrics = llm_result.get("metrics", {})

    # Serialize to JSON
    try:
        issues_json_str = json.dumps(issues)
        metrics_json_str = json.dumps(metrics)
        strengths_json_str = json.dumps(strengths)
    except Exception:
        issues_json_str = "[]"
        metrics_json_str = "{}"
        strengths_json_str = "[]"
        issues = []
        metrics = {}
        strengths = []

    # Save to DB
    try:
        review_id = insert_review(
            filenames=filenames,
            summary=summary,
            details=details,
            raw_response=raw_response,
            issues_json=issues_json_str,
            quality_score=quality_score,
            metrics_json=metrics_json_str,
            strengths_json=strengths_json_str,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    issue_models = [Issue(**issue) for issue in issues if isinstance(issue, dict)]

    return ReviewResponse(
        id=review_id,
        summary=summary,
        details=details,
        issues=issue_models,
        raw_response=raw_response,
        quality_score=quality_score,
        strengths=strengths,
        metrics=metrics,
    )


@app.get("/api/reports", response_model=List[ReviewListItem])
def list_recent_reports(limit: int = 10):
    """
    Return the most recent saved reviews.
    Useful for showing history in the dashboard.
    """
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 100",
        )

    try:
        rows = fetch_recent_reviews(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    return [
        ReviewListItem(
            id=row["id"],
            created_at=str(row["created_at"]),
            filenames=row["filenames"],
            summary=row["summary"],
            quality_score=row.get("quality_score", 0.0),
        )
        for row in rows
    ]


@app.get("/api/reports/{report_id}", response_model=ReviewDetail)
def get_report(report_id: int):
    """
    Fetch a single review by its ID.
    """
    try:
        row = fetch_review_by_id(report_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    issues: List[Issue] = []
    strengths: List[str] = []
    metrics: Dict = {}
    
    issues_json_str = row.get("issues_json")
    if issues_json_str:
        try:
            raw_issues = json.loads(issues_json_str)
            if isinstance(raw_issues, list):
                issues = [Issue(**issue) for issue in raw_issues if isinstance(issue, dict)]
        except Exception:
            issues = []
    
    strengths_json_str = row.get("strengths_json")
    if strengths_json_str:
        try:
            strengths = json.loads(strengths_json_str)
            if not isinstance(strengths, list):
                strengths = []
        except Exception:
            strengths = []
    
    metrics_json_str = row.get("metrics_json")
    if metrics_json_str:
        try:
            metrics = json.loads(metrics_json_str)
            if not isinstance(metrics, dict):
                metrics = {}
        except Exception:
            metrics = {}

    return ReviewDetail(
        id=row["id"],
        created_at=str(row["created_at"]),
        filenames=row["filenames"],
        summary=row["summary"],
        details=row["details"],
        issues=issues,
        raw_response=row.get("raw_response"),
        quality_score=row.get("quality_score", 0.0),
        strengths=strengths,
        metrics=metrics,
    )