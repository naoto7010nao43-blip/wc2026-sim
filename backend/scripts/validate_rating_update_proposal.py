"""Validate a future rating-update proposal before any data is changed.

This script is intentionally conservative. It checks that a proposal contains
player-level evidence, bounded numeric deltas, and a benchmark comparison
before Codex considers a data-changing spec. It never applies changes.

Usage:
  ./venv/Scripts/python.exe scripts/validate_rating_update_proposal.py proposal.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ALLOWED_SOURCE_TIERS = {"S", "A", "B"}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}
ALLOWED_ACTIONS = {"upgrade", "downgrade", "role_only", "monitor"}

MAX_OVERALL_DELTA = 5
MAX_ATTRIBUTE_DELTA = 8

OVERALL_FIELDS = {"overall", "positionOverall"}
RATING_FIELDS = OVERALL_FIELDS | {
    "attack",
    "finishing",
    "shotPower",
    "passing",
    "chanceCreation",
    "dribbling",
    "ballCarrying",
    "crossing",
    "setPiece",
    "defense",
    "tackling",
    "interception",
    "aerialDefense",
    "physical",
    "speed",
    "acceleration",
    "stamina",
    "strength",
    "mentality",
    "composure",
    "workRate",
    "pressing",
    "decisionMaking",
    "positioning",
    "goalkeeperHandling",
    "goalkeeperReflexes",
    "goalkeeperDistribution",
    "currentForm",
    "startingProbability",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_change(change: dict, index: int) -> list[str]:
    errors = []
    prefix = f"changes[{index}]"

    for required in ("playerId", "teamId", "field", "currentValue", "proposedValue", "action", "sourceTier", "confidence", "reason"):
        if required not in change:
            errors.append(f"{prefix}.{required} is required")

    field = change.get("field")
    if field is not None and field not in RATING_FIELDS:
        errors.append(f"{prefix}.field {field!r} is not an allowed rating field")

    if change.get("sourceTier") not in ALLOWED_SOURCE_TIERS:
        errors.append(f"{prefix}.sourceTier must be one of {sorted(ALLOWED_SOURCE_TIERS)}")

    if change.get("confidence") not in ALLOWED_CONFIDENCE:
        errors.append(f"{prefix}.confidence must be one of {sorted(ALLOWED_CONFIDENCE)}")

    if change.get("action") not in ALLOWED_ACTIONS:
        errors.append(f"{prefix}.action must be one of {sorted(ALLOWED_ACTIONS)}")

    evidence = change.get("evidenceRefs")
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"{prefix}.evidenceRefs must be a non-empty list")

    current = change.get("currentValue")
    proposed = change.get("proposedValue")
    if numeric(current) and numeric(proposed):
        max_delta = MAX_OVERALL_DELTA if field in OVERALL_FIELDS else MAX_ATTRIBUTE_DELTA
        actual_delta = abs(float(proposed) - float(current))
        if actual_delta > max_delta:
            errors.append(f"{prefix} changes {field} by {actual_delta:g}, above max {max_delta}")
    elif "currentValue" in change and "proposedValue" in change:
        errors.append(f"{prefix}.currentValue and proposedValue must both be numeric")

    reason = change.get("reason")
    if isinstance(reason, str) and len(reason.strip()) < 20:
        errors.append(f"{prefix}.reason is too short for a data-changing proposal")

    return errors


def validate_benchmark_comparison(value: Any) -> list[str]:
    errors = []
    if not isinstance(value, dict):
        return ["benchmarkComparison is required and must be an object"]
    if value.get("status") != "pass":
        errors.append("benchmarkComparison.status must be 'pass'")
    if "beforeReport" not in value or "afterReport" not in value:
        errors.append("benchmarkComparison.beforeReport and afterReport are required")
    if "watchlistImplausibleReduction" not in value:
        errors.append("benchmarkComparison.watchlistImplausibleReduction is required")
    elif not numeric(value["watchlistImplausibleReduction"]):
        errors.append("benchmarkComparison.watchlistImplausibleReduction must be numeric")
    return errors


def validate_proposal(proposal: dict) -> dict:
    errors = []
    warnings = []

    for required in ("proposalVersion", "generatedAt", "summary", "changes", "benchmarkComparison"):
        if required not in proposal:
            errors.append(f"{required} is required")

    changes = proposal.get("changes")
    if not isinstance(changes, list) or not changes:
        errors.append("changes must be a non-empty list")
    elif len(changes) > 60:
        warnings.append("proposal contains more than 60 field changes; consider splitting into smaller reviewed specs")
    else:
        seen = set()
        for i, change in enumerate(changes):
            if not isinstance(change, dict):
                errors.append(f"changes[{i}] must be an object")
                continue
            key = (change.get("playerId"), change.get("field"))
            if key in seen:
                errors.append(f"duplicate change for player/field {key}")
            seen.add(key)
            errors.extend(validate_change(change, i))

    errors.extend(validate_benchmark_comparison(proposal.get("benchmarkComparison")))

    return {
        "valid": not errors,
        "errorCount": len(errors),
        "warningCount": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("proposal", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = validate_proposal(load_json(args.proposal))
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(text)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
