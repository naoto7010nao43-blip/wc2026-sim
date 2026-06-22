"""Tier B manager rating: carries forward the existing 3-axis tactical
profile (press_intensity/possession_style/defensive_line_height,
previously embedded directly in Team.tactical_profile) as a properly
identified, joinable entity. Not a new data source -- this is the
existing researched values, now structured and dataConfidence-tagged
rather than an untagged dict. A fuller multi-axis coaching profile (the
~12 axes in the user's original spec) is future work -- see roadmap.
"""

from app.rating_v2.types import ManagerRatingV2


def compute_manager_rating_v2(manager_id: str, team_code: str, tactical_profile: dict | None) -> ManagerRatingV2:
    profile = tactical_profile or {}
    return ManagerRatingV2(
        manager_id=manager_id,
        team_code=team_code,
        press_intensity=int(round(profile.get("press_intensity", 50))),
        possession_style=int(round(profile.get("possession_style", 50))),
        defensive_line_height=int(round(profile.get("defensive_line_height", 50))),
        data_confidence="estimated",
    )
