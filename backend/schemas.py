from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class Issue(BaseModel):
    id: str
    file: str
    line_start: int
    line_end: int
    severity: str
    category: str
    message: str
    suggestion: str
    code_patch: Optional[str] = ""


class ReviewResponse(BaseModel):
    """
    Response after creating a review (POST /api/review).
    Includes the assigned database ID and structured issues.
    """
    id: int
    summary: str
    details: str
    issues: List[Issue] = []
    raw_response: Optional[str] = None
    quality_score: float = 0.0
    strengths: List[str] = []
    metrics: Dict[str, Any] = {}


class ReviewListItem(BaseModel):
    """
    A lightweight representation of a review to show in lists.
    """
    id: int
    created_at: str
    filenames: str
    summary: str
    quality_score: float = 0.0


class ReviewDetail(BaseModel):
    """
    Full review details fetched from DB.
    """
    id: int
    created_at: str
    filenames: str
    summary: str
    details: str
    issues: List[Issue] = []
    raw_response: Optional[str] = None
    quality_score: float = 0.0
    strengths: List[str] = []
    metrics: Dict[str, Any] = {}