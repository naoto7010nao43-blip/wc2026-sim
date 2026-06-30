"""Regression guardrail: every /api/model-diagnostics/* summary is rendered
directly in the Japanese-only /data-review UI. English copy has slipped into
these reports three separate times (Specs 011, 012, 013), each caught only by
manual screenshot review. This locks in that the user-facing text fields stay
Japanese so a fourth occurrence fails CI instead of requiring another
screenshot review.
"""

import re

from app.services.model_diagnostics import (
    get_external_data_verification_summary,
    get_manager_tactical_trust_summary,
    get_model_calibration_summary,
    get_rating_decision_audit_summary,
    get_rating_review_workbench_summary,
    get_release_readiness_summary,
    get_simulation_stability_summary,
    get_squad_gap_summary,
    get_source_provenance_audit_summary,
    get_substitution_model_gap_summary,
    get_team_review_summary,
)

JAPANESE_CHAR = re.compile(r"[぀-ヿ一-鿿]")
COPY_FIELDS = {
    "note",
    "review_reasons",
    "review_summary_ja",
    "reason_ja",
    "recommendations_ja",
    "recommendationsJa",
    "label",
    "currentBehavior",
    "precisionRiskJa",
    "evidenceNeededJa",
    "recommendedNextAction",
    "nonBlockingWarnings",
}


def _assert_japanese_copy(value, path):
    if isinstance(value, str):
        assert JAPANESE_CHAR.search(value), f"expected Japanese text at {path!r}, got: {value!r}"
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _assert_japanese_copy(item, f"{path}[{i}]")


def _walk(obj, path=""):
    if isinstance(obj, dict):
        for key, value in obj.items():
            child_path = f"{path}.{key}" if path else key
            if key in COPY_FIELDS:
                _assert_japanese_copy(value, child_path)
            _walk(value, child_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _walk(item, f"{path}[{i}]")


def test_team_review_summary_copy_is_japanese():
    _walk(get_team_review_summary())


def test_release_readiness_summary_copy_is_japanese():
    _walk(get_release_readiness_summary())


def test_external_data_verification_summary_copy_is_japanese():
    _walk(get_external_data_verification_summary())


def test_squad_gap_summary_copy_is_japanese():
    _walk(get_squad_gap_summary())


def test_manager_tactical_trust_summary_copy_is_japanese():
    _walk(get_manager_tactical_trust_summary())


def test_rating_review_workbench_summary_copy_is_japanese():
    _walk(get_rating_review_workbench_summary())


def test_source_provenance_audit_summary_copy_is_japanese():
    _walk(get_source_provenance_audit_summary())


def test_rating_decision_audit_summary_copy_is_japanese():
    _walk(get_rating_decision_audit_summary())


def test_model_calibration_summary_copy_is_japanese():
    _walk(get_model_calibration_summary())


def test_simulation_stability_summary_copy_is_japanese():
    _walk(get_simulation_stability_summary())


def test_substitution_model_gap_summary_copy_is_japanese():
    _walk(get_substitution_model_gap_summary())
