from fastapi import APIRouter

from app.schemas.model_diagnostics import TeamReviewSummary
from app.services.model_diagnostics import get_team_review_summary

router = APIRouter(prefix="/api/model-diagnostics", tags=["model-diagnostics"])


@router.get("/team-review", response_model=TeamReviewSummary)
def get_team_review():
    return get_team_review_summary()
