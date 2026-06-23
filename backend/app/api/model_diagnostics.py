from fastapi import APIRouter

from app.schemas.model_diagnostics import ManagerTacticalTrustSummary, SquadGapSummary, TeamReviewSummary
from app.services.model_diagnostics import (
    get_manager_tactical_trust_summary,
    get_squad_gap_summary,
    get_team_review_summary,
)

router = APIRouter(prefix="/api/model-diagnostics", tags=["model-diagnostics"])


@router.get("/team-review", response_model=TeamReviewSummary)
def get_team_review():
    return get_team_review_summary()


@router.get("/squad-gaps", response_model=SquadGapSummary)
def get_squad_gaps():
    return get_squad_gap_summary()


@router.get("/manager-tactical-trust", response_model=ManagerTacticalTrustSummary)
def get_manager_tactical_trust():
    return get_manager_tactical_trust_summary()
