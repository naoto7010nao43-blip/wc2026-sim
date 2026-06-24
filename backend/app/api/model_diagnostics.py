from fastapi import APIRouter

from app.schemas.model_diagnostics import (
    ManagerTacticalTrustSummary,
    ModelCalibrationSummary,
    RatingDecisionAuditSummary,
    RatingReviewWorkbenchSummary,
    ReleaseReadinessSummary,
    SimulationStabilitySummary,
    SourceProvenanceAuditSummary,
    SquadGapSummary,
    SubstitutionModelGapSummary,
    TeamReviewSummary,
)
from app.services.model_diagnostics import (
    get_manager_tactical_trust_summary,
    get_model_calibration_summary,
    get_rating_decision_audit_summary,
    get_rating_review_workbench_summary,
    get_release_readiness_summary,
    get_simulation_stability_summary,
    get_source_provenance_audit_summary,
    get_squad_gap_summary,
    get_substitution_model_gap_summary,
    get_team_review_summary,
)

router = APIRouter(prefix="/api/model-diagnostics", tags=["model-diagnostics"])


@router.get("/team-review", response_model=TeamReviewSummary)
def get_team_review():
    return get_team_review_summary()


@router.get("/release-readiness", response_model=ReleaseReadinessSummary)
def get_release_readiness():
    return get_release_readiness_summary()


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


@router.get("/model-calibration", response_model=ModelCalibrationSummary)
def get_model_calibration():
    return get_model_calibration_summary()


@router.get("/simulation-stability", response_model=SimulationStabilitySummary)
def get_simulation_stability():
    return get_simulation_stability_summary()


@router.get("/substitution-model-gap", response_model=SubstitutionModelGapSummary)
def get_substitution_model_gap():
    return get_substitution_model_gap_summary()
