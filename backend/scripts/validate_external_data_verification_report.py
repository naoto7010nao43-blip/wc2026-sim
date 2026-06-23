"""Validate Claude/Codex external data verification candidate reports.

This is a pre-Codex-review gate. It does not decide whether a data candidate is
true, and it never applies seed/rating/formula changes. It checks whether a
research report is structured, sourced, mapped to the simulator honestly, and
useful enough for a later Codex data-changing spec.

Usage:
  ./venv/Scripts/python.exe scripts/validate_external_data_verification_report.py reports/external_data_verification_candidates_2026-06-24.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent.parent
SEED_DIR = BACKEND_DIR / "data" / "seed"

ALLOWED_SOURCE_TIERS = {"S", "A", "B", "C"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
RECOGNIZED_CATEGORIES = {
    "managerStatus",
    "formationCandidates",
    "tacticalProfileCandidates",
    "keyPlayerStatusCandidates",
    "nationalStrengthContext",
    "substitutionTendencyCandidates",
}
EXISTING_FIELD_CATEGORIES = {
    "managerStatus": {"manager_name"},
    "formationCandidates": {"default_formation"},
    "tacticalProfileCandidates": {
        "press_intensity",
        "possession_style",
        "defensive_line_height",
        "default_formation",
    },
    "keyPlayerStatusCandidates": {
        "seed_roster",
        "player_rating",
        "club_name",
        "availability_status",
        "starting_probability",
    },
    "nationalStrengthContext": {"fifa_rank", "team_strength_rating"},
}
FUTURE_ONLY_CATEGORIES = {"substitutionTendencyCandidates"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_team_ids(seed_dir: Path = SEED_DIR) -> set[str]:
    teams = load_json(seed_dir / "teams.json")
    return {row["id"] for row in teams}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def source_tier(candidate: dict) -> str | None:
    if isinstance(candidate.get("sourceTier"), str):
        return candidate["sourceTier"]
    sources = as_list(candidate.get("sources"))
    tiers = [row.get("tier") for row in sources if isinstance(row, dict) and isinstance(row.get("tier"), str)]
    if not tiers:
        return None
    order = {"S": 0, "A": 1, "B": 2, "C": 3}
    return sorted(tiers, key=lambda tier: order.get(tier, 99))[0]


def source_count(candidate: dict) -> int:
    sources = as_list(candidate.get("sources"))
    if sources:
        return sum(1 for row in sources if isinstance(row, dict))
    return 1 if candidate.get("sourceName") or candidate.get("url") else 0


def confidence(candidate: dict) -> str | None:
    value = candidate.get("confidence")
    return value if isinstance(value, str) else None


def mapping_target(candidate: dict) -> str | None:
    for key in ("mapsTo", "existingField", "targetField", "field"):
        value = candidate.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def action_category(candidate: dict) -> str | None:
    for key in ("candidateCategory", "category", "recommendedActionType"):
        value = candidate.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def candidate_text(candidate: dict) -> str:
    parts = []
    for key in ("claim", "summary", "reason", "note", "evidence", "recommendation"):
        value = candidate.get(key)
        if isinstance(value, str):
            parts.append(value)
    return " ".join(parts).strip()


def candidate_quality_score(category: str, candidate: dict) -> int:
    tier = source_tier(candidate)
    conf = confidence(candidate)
    target = mapping_target(candidate)
    score = 0

    if tier == "S":
        score += 5
    elif tier == "A":
        score += 4
    elif tier == "B":
        score += 2
    elif tier == "C":
        score -= 2

    if conf == "high":
        score += 3
    elif conf == "medium":
        score += 2
    elif conf == "low":
        score += 0

    if source_count(candidate) >= 2:
        score += 1

    if category in EXISTING_FIELD_CATEGORIES and target in EXISTING_FIELD_CATEGORIES[category]:
        score += 3
    elif category in FUTURE_ONLY_CATEGORIES:
        score -= 1

    if action_category(candidate) in {"safe factual candidate", "tactical-profile candidate", "roster/availability candidate"}:
        score += 1
    if action_category(candidate) in {"future-engine candidate", "ambiguous candidate"}:
        score -= 1

    return score


def impact_band(score: int) -> str:
    if score >= 10:
        return "high"
    if score >= 6:
        return "medium"
    return "low"


def use_tier(category: str, candidate: dict, score: int) -> str:
    tier = source_tier(candidate)
    conf = confidence(candidate)
    target = mapping_target(candidate)
    if category in FUTURE_ONLY_CATEGORIES:
        return "future_engine_candidate"
    if tier in {"S", "A"} and conf in {"high", "medium"} and score >= 8:
        return "ready_for_codex_review"
    if tier in {"A", "B"} and score >= 5:
        return "provisional_context"
    if target or candidate_text(candidate):
        return "review_question"
    return "insufficient_detail"


def validate_candidate(category: str, candidate: Any, team_id: str, index: int) -> tuple[list[str], list[str], dict]:
    errors = []
    warnings = []
    path = f"teams[{team_id}].{category}[{index}]"
    if not isinstance(candidate, dict):
        return [f"{path} must be an object"], warnings, {"impactBand": "low", "qualityScore": 0}

    tier = source_tier(candidate)
    conf = confidence(candidate)
    target = mapping_target(candidate)
    text = candidate_text(candidate)
    score = candidate_quality_score(category, candidate)

    if tier not in ALLOWED_SOURCE_TIERS:
        warnings.append(f"{path} has no recognized source tier; keep as review question until sourced")
    if conf not in ALLOWED_CONFIDENCE:
        warnings.append(f"{path}.confidence is missing or unknown; keep as provisional context")
    if source_count(candidate) == 0:
        warnings.append(f"{path} has no source reference; do not use for data changes")
    if len(text) < 20:
        warnings.append(f"{path} has very short claim/evidence text")

    if category in FUTURE_ONLY_CATEGORIES:
        if action_category(candidate) != "future-engine candidate":
            warnings.append(f"{path} should be labelled candidateCategory='future-engine candidate'")
        if target and target not in {"future_engine_feature", "substitution_tendency"}:
            warnings.append(f"{path} maps to {target!r}, but substitutions currently have no engine field")
    elif category in EXISTING_FIELD_CATEGORIES:
        allowed = EXISTING_FIELD_CATEGORIES[category]
        if not target:
            warnings.append(f"{path} should state mapsTo/existingField so Codex can judge implementation impact")
        elif target not in allowed:
            warnings.append(f"{path} maps to {target!r}, expected one of {sorted(allowed)}")

    if tier == "C":
        warnings.append(f"{path} uses Tier C evidence; keep as review question only")
    if tier == "B" and conf == "high":
        warnings.append(f"{path} is Tier B but high confidence; verify before using for data changes")

    return errors, warnings, {
        "teamId": team_id,
        "category": category,
        "qualityScore": score,
        "impactBand": impact_band(score),
        "useTier": use_tier(category, candidate, score),
        "sourceTier": tier,
        "confidence": conf,
        "mapsTo": target,
        "candidateCategory": action_category(candidate),
        "summary": text[:180],
    }


def validate_team(team: Any, known_team_ids: set[str]) -> tuple[list[str], list[str], list[dict]]:
    errors = []
    warnings = []
    scored = []
    if not isinstance(team, dict):
        return ["teams[] entries must be objects"], warnings, scored

    team_id = team.get("teamId")
    if team_id not in known_team_ids:
        errors.append(f"teams[].teamId {team_id!r} is not in backend/data/seed/teams.json")

    for category in RECOGNIZED_CATEGORIES:
        value = team.get(category, [])
        if value is None:
            continue
        if not isinstance(value, list):
            errors.append(f"teams[{team_id}].{category} must be a list")
            continue
        for index, candidate in enumerate(value):
            candidate_errors, candidate_warnings, score = validate_candidate(category, candidate, str(team_id), index)
            errors.extend(candidate_errors)
            warnings.extend(candidate_warnings)
            scored.append(score)

    unknown_categories = sorted(
        key for key, value in team.items()
        if key.endswith("Candidates") or key.endswith("Context") or key.endswith("Status")
        if key not in RECOGNIZED_CATEGORIES
    )
    for key in unknown_categories:
        warnings.append(f"teams[{team_id}] has unrecognized research category {key!r}")

    return errors, warnings, scored


def validate_report(report: dict, known_team_ids: set[str] | None = None) -> dict:
    known_team_ids = known_team_ids or load_team_ids()
    errors = []
    warnings = []
    scored_candidates = []

    for required in ("generatedAt", "scope", "teams"):
        if required not in report:
            errors.append(f"{required} is required")

    teams = report.get("teams")
    if not isinstance(teams, list):
        errors.append("teams must be a list")
        teams = []

    seen_team_ids = set()
    for team in teams:
        if isinstance(team, dict) and isinstance(team.get("teamId"), str):
            if team["teamId"] in seen_team_ids:
                errors.append(f"duplicate teamId {team['teamId']}")
            seen_team_ids.add(team["teamId"])
        team_errors, team_warnings, team_scores = validate_team(team, known_team_ids)
        errors.extend(team_errors)
        warnings.extend(team_warnings)
        scored_candidates.extend(team_scores)

    scope = report.get("scope")
    if isinstance(scope, dict):
        covered = set(scope.get("coveredTeams") or [])
        if covered and covered != seen_team_ids:
            warnings.append("scope.coveredTeams does not match teams[].teamId exactly")
        unknown_covered = sorted(covered - known_team_ids)
        if unknown_covered:
            errors.append("scope.coveredTeams includes unknown team IDs: " + ", ".join(unknown_covered))
    elif scope is not None:
        errors.append("scope must be an object")

    category_counts = Counter(row["category"] for row in scored_candidates)
    impact_counts = Counter(row["impactBand"] for row in scored_candidates)
    use_tier_counts = Counter(row["useTier"] for row in scored_candidates)
    future_engine_count = sum(1 for row in scored_candidates if row["category"] in FUTURE_ONLY_CATEGORIES)
    existing_field_count = sum(
        1 for row in scored_candidates
        if row["mapsTo"] and row["category"] in EXISTING_FIELD_CATEGORIES
        and row["mapsTo"] in EXISTING_FIELD_CATEGORIES[row["category"]]
    )
    by_team: dict[str, list[dict]] = defaultdict(list)
    for row in scored_candidates:
        by_team[row["teamId"]].append(row)

    team_priorities = []
    for team_id, rows in by_team.items():
        high_count = sum(1 for row in rows if row["impactBand"] == "high")
        medium_count = sum(1 for row in rows if row["impactBand"] == "medium")
        future_count = sum(1 for row in rows if row["category"] in FUTURE_ONLY_CATEGORIES)
        priority_score = sum(row["qualityScore"] for row in rows if row["impactBand"] in {"high", "medium"})
        team_priorities.append({
            "teamId": team_id,
            "priorityScore": priority_score,
            "highImpactCandidateCount": high_count,
            "mediumImpactCandidateCount": medium_count,
            "futureEngineCandidateCount": future_count,
        })
    team_priorities.sort(key=lambda row: (-row["priorityScore"], row["teamId"]))

    return {
        "valid": not errors,
        "errorCount": len(errors),
        "warningCount": len(warnings),
        "candidateCount": len(scored_candidates),
        "coveredTeamCount": len(seen_team_ids),
        "categoryCounts": dict(sorted(category_counts.items())),
        "impactCounts": dict(sorted(impact_counts.items())),
        "useTierCounts": dict(sorted(use_tier_counts.items())),
        "existingFieldCandidateCount": existing_field_count,
        "futureEngineCandidateCount": future_engine_count,
        "topTeamPriorities": team_priorities[:12],
        "topCandidatePreviews": sorted(scored_candidates, key=lambda row: (-row["qualityScore"], row["teamId"]))[:20],
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    validation = validate_report(load_json(args.report))
    text = json.dumps(validation, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(text)
    return 0 if validation["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
