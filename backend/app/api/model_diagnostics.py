from fastapi import APIRouter

from app.schemas.model_diagnostics import (
    ManagerTacticalTrustSummary,
    RatingDecisionAuditSummary,
    RatingReviewWorkbenchSummary,
    SourceProvenanceAuditSummary,
    SquadGapSummary,
    TeamReviewSummary,
)
from app.services.model_diagnostics import (
    get_manager_tactical_trust_summary,
    get_rating_decision_audit_summary,
    get_rating_review_workbench_summary,
    get_source_provenance_audit_summary,
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


@router.get("/rating-review-workbench", response_model=RatingReviewWorkbenchSummary)
def get_rating_review_workbench():
    return get_rating_review_workbench_summary()


@router.get("/source-provenance-audit", response_model=SourceProvenanceAuditSummary)
def get_source_provenance_audit():
    return get_source_provenance_audit_summary()


@router.get("/rating-decision-audit", response_model=RatingDecisionAuditSummary)
def get_rating_decision_audit():
    return get_rating_decision_audit_summary()
