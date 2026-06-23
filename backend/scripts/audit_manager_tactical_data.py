"""Read-only audit for manager and tactical-profile trust.

This does not change seed data, ratings, formulas, or prediction behavior.
It compares the current team tactical profiles, official manager names, and
estimated manager tactical ratings, then writes a review-priority report.

Usage: ./venv/Scripts/python.exe scripts/audit_manager_tactical_data.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

TACTICAL_KEYS = ("press_intensity", "possession_style", "defensive_line_height")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def latest_report(pattern: str) -> dict | None:
    if not REPORTS_DIR.exists():
        return None
    matches = sorted(REPORTS_DIR.glob(pattern))
    if not matches:
        return None
    return load_json(matches[-1])


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.casefold().replace(".", "").split())


def profile_key(profile: dict | None) -> tuple:
    if not profile:
        return tuple()
    return tuple(profile.get(k) for k in TACTICAL_KEYS)


def duplicate_profile_lookup(teams: list[dict]) -> dict[str, list[str]]:
    grouped: dict[tuple, list[str]] = {}
    for team in teams:
        key = profile_key(team.get("tactical_profile"))
        if not key:
            continue
        grouped.setdefault(key, []).append(team["id"])

    lookup: dict[str, list[str]] = {}
    for team_ids in grouped.values():
        if len(team_ids) < 2:
            continue
        for team_id in team_ids:
            lookup[team_id] = sorted(team_ids)
    return lookup


def team_review_lookup(team_review_report: dict | None) -> dict[str, dict]:
    if not team_review_report:
        return {}
    return {row["team_id"]: row for row in team_review_report.get("teams", [])}


def compute_review_score(
    *,
    manager_name_mismatch: bool,
    missing_manager_rating: bool,
    missing_tactical_basis: bool,
    duplicate_profile_team_count: int,
    top_twenty_fifa_rank: bool,
    team_review_band: str | None,
) -> float:
    score = 0.0
    if manager_name_mismatch:
        score += 30.0
    if missing_manager_rating:
        score += 20.0
    if team_review_band == "high":
        score += 15.0
    elif team_review_band == "medium":
        score += 7.0
    if top_twenty_fifa_rank and missing_tactical_basis:
        score += 10.0
    elif missing_tactical_basis:
        score += 5.0
    if duplicate_profile_team_count >= 2:
        score += min(duplicate_profile_team_count * 2.0, 12.0)
    return round(score, 1)


def priority_band(score: float) -> str:
    if score >= 25.0:
        return "high"
    if score >= 10.0:
        return "medium"
    return "low"


def build_reasons(
    *,
    manager_name_mismatch: bool,
    missing_manager_rating: bool,
    missing_tactical_basis: bool,
    duplicate_profile_team_count: int,
    top_twenty_fifa_rank: bool,
    team_review_band: str | None,
) -> list[str]:
    reasons: list[str] = []
    if manager_name_mismatch:
        reasons.append("監督名がシードデータと公式データで一致していません")
    if missing_manager_rating:
        reasons.append("監督の戦術評価データが見つかりません")
    if team_review_band == "high":
        reasons.append("チームデータレビューの優先度が高です")
    elif team_review_band == "medium":
        reasons.append("チームデータレビューの優先度が中です")
    if missing_tactical_basis and top_twenty_fifa_rank:
        reasons.append("FIFAランク20位以内のチームですが、戦術プロフィールの根拠情報がありません")
    elif missing_tactical_basis:
        reasons.append("戦術プロフィールの根拠情報がありません")
    if duplicate_profile_team_count >= 2:
        reasons.append(f"他の{duplicate_profile_team_count - 1}チームと同じ戦術値の組み合わせを共有しています")
    if not reasons:
        reasons.append("現時点で監督・戦術データの信頼性に関する重大な指摘はありません")
    return reasons


def build_team_row(
    team: dict,
    official_team: dict | None,
    official_manager: dict | None,
    manager_rating: dict | None,
    duplicate_profiles: dict[str, list[str]],
    team_review_rows: dict[str, dict],
) -> dict:
    team_id = team["id"]
    seed_profile = team.get("tactical_profile") or {}
    official_profile = (official_team or {}).get("tacticalProfile") or {}
    seed_manager_name = seed_profile.get("manager_name")
    official_manager_name = (official_manager or {}).get("name")
    official_profile_manager_name = official_profile.get("manager_name")

    manager_names = [
        normalize_name(seed_manager_name),
        normalize_name(official_manager_name),
        normalize_name(official_profile_manager_name),
    ]
    present_manager_names = {name for name in manager_names if name}
    manager_name_mismatch = len(present_manager_names) > 1
    missing_manager_rating = manager_rating is None
    missing_tactical_basis = not bool(team.get("_tactical_profile_basis"))
    fifa_rank = team.get("fifa_rank")
    top_twenty_fifa_rank = fifa_rank is not None and fifa_rank <= 20
    duplicate_profile_team_ids = duplicate_profiles.get(team_id, [])
    team_review_band = (team_review_rows.get(team_id) or {}).get("priority_band")

    score = compute_review_score(
        manager_name_mismatch=manager_name_mismatch,
        missing_manager_rating=missing_manager_rating,
        missing_tactical_basis=missing_tactical_basis,
        duplicate_profile_team_count=len(duplicate_profile_team_ids),
        top_twenty_fifa_rank=top_twenty_fifa_rank,
        team_review_band=team_review_band,
    )

    return {
        "team_id": team_id,
        "team_name": team["name"],
        "fifa_rank": fifa_rank,
        "default_formation": team.get("default_formation"),
        "manager_name_seed": seed_manager_name,
        "manager_name_official": official_manager_name,
        "manager_name_official_profile": official_profile_manager_name,
        "manager_name_mismatch": manager_name_mismatch,
        "manager_rating_confidence": (manager_rating or {}).get("dataConfidence"),
        "missing_manager_rating": missing_manager_rating,
        "has_tactical_basis": not missing_tactical_basis,
        "tactical_profile": {key: seed_profile.get(key) for key in TACTICAL_KEYS},
        "duplicate_profile_team_ids": duplicate_profile_team_ids,
        "team_review_priority_band": team_review_band,
        "review_score": score,
        "review_band": priority_band(score),
        "review_reasons": build_reasons(
            manager_name_mismatch=manager_name_mismatch,
            missing_manager_rating=missing_manager_rating,
            missing_tactical_basis=missing_tactical_basis,
            duplicate_profile_team_count=len(duplicate_profile_team_ids),
            top_twenty_fifa_rank=top_twenty_fifa_rank,
            team_review_band=team_review_band,
        ),
    }


def build_report(
    teams: list[dict],
    official_teams: list[dict],
    official_managers: list[dict],
    manager_ratings: list[dict],
    team_review_report: dict | None,
) -> dict:
    official_team_by_id = {row["teamId"]: row for row in official_teams}
    official_manager_by_team = {row["teamCode"]: row for row in official_managers}
    manager_rating_by_team = {row["teamCode"]: row for row in manager_ratings}
    duplicate_profiles = duplicate_profile_lookup(teams)
    review_rows = team_review_lookup(team_review_report)

    rows = [
        build_team_row(
            team=team,
            official_team=official_team_by_id.get(team["id"]),
            official_manager=official_manager_by_team.get(team["id"]),
            manager_rating=manager_rating_by_team.get(team["id"]),
            duplicate_profiles=duplicate_profiles,
            team_review_rows=review_rows,
        )
        for team in teams
    ]
    rows.sort(key=lambda row: (-row["review_score"], row["team_id"]))

    band_counts = {"high": 0, "medium": 0, "low": 0}
    for row in rows:
        band_counts[row["review_band"]] += 1

    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "note": (
            "監督名・戦術プロフィールデータの信頼性を示す読み取り専用の監査です。"
            "監督名の不一致、戦術プロフィールの根拠情報の欠如、戦術値の重複、"
            "上流のチームデータレビュー優先度などから、人によるレビューが望ましいチームを示します。"
            "試合予測そのものは変更しません。"
        ),
        "sourceReports": [
            {"name": "team_data_review_plan", "generatedAt": (team_review_report or {}).get("generatedAt")}
        ],
        "teamCount": len(rows),
        "bandCounts": band_counts,
        "teams": rows,
    }


def main() -> int:
    teams = load_json(SEED_DIR / "teams.json")
    official_teams = load_json(SEED_DIR / "teams2026_official.json")
    official_managers = load_json(SEED_DIR / "managers2026_official.json")
    manager_ratings = load_json(SEED_DIR / "managerRatings2026_estimated.json")
    team_review_report = latest_report("team_data_review_plan_*.json")

    report = build_report(teams, official_teams, official_managers, manager_ratings, team_review_report)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = REPORTS_DIR / f"manager_tactical_data_audit_{date_str}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {out_path}")
    print(f"Teams: {report['teamCount']} (high={report['bandCounts']['high']}, medium={report['bandCounts']['medium']}, low={report['bandCounts']['low']})")
    print("Top 8 manager/tactical review priorities:")
    for row in report["teams"][:8]:
        print(f"  {row['team_id']:4s} score={row['review_score']:5.1f} band={row['review_band']:6s} {', '.join(row['review_reasons'][:2])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
