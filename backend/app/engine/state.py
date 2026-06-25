"""Runtime (in-memory, per-simulation) state — distinct from persisted models.

PlayerState/TeamState track live position and stamina during a single
match simulation; they are built once from persisted Player rows at the
start of simulate_match() and discarded afterward.
"""

from dataclasses import dataclass, field

from app.engine.formations import FORMATIONS, SLOT_POSITION_ALIASES, Formation

# Per-manager substitution tendency, estimated/external metadata rather than
# confirmed fact (see DATA_GOVERNANCE_POLICY.md). Every field defaults to a
# neutral value chosen so that an unset/neutral profile reproduces exactly
# the prior fatigue-only, fixed-window substitution behavior -- this lets
# the feature exist without changing any match's output until a specific
# team is given a non-neutral, source-backed profile.
NEUTRAL_SUBSTITUTION_PROFILE: dict = {
    # Minutes earlier(-)/later(+) than the base substitution window start.
    "first_sub_minute_bias": 0.0,
    # 0-1 add-on to substitution chance per minute while trailing.
    "trailing_aggression": 0.0,
    # 0-1 add-on to substitution chance per minute while leading.
    "leading_defensive_bias": 0.0,
    # 0-1; 0.5 is neutral (chance multiplier 1.0x), 1.0 doubles it, 0.0 halves it.
    "bench_trust": 0.5,
    # 0-1; 1.0 always prefers a same-position bench replacement when one
    # exists (current/prior behavior); lower values sometimes pick the best
    # available bench player regardless of position.
    "like_for_like_preference": 1.0,
    # 0-1; recorded for future extra-time/penalty-shootout substitution
    # prep logic. Not yet wired to any behavior -- evidence for this field
    # is too sparse across researched teams to implement safely (see Spec
    # 018 Phase 5).
    "late_penalty_prep_bias": 0.0,
}


@dataclass
class PlayerState:
    player_id: str
    name: str
    slot_position: str  # the formation slot they're filling (e.g. "CB", "LW")
    primary_position: str
    attributes: dict
    overall: int
    stamina_max: int
    current_stamina: float
    home_x: float
    home_y: float
    x: float
    y: float
    name_ja: str | None = None

    @property
    def display_name(self) -> str:
        return self.name_ja or self.name

    def stamina_factor(self) -> float:
        """1.0 at full stamina, decays toward ~0.6 as stamina depletes."""
        ratio = self.current_stamina / max(self.stamina_max, 1)
        return 0.6 + 0.4 * max(0.0, min(1.0, ratio))


@dataclass
class TeamState:
    team_id: str
    formation: Formation
    lineup: list[PlayerState]
    score: int = 0
    attacking_direction: int = 1  # 1 = attacks toward x=100, -1 = toward x=0
    # {"manager_name": str, "press_intensity": 0-100, "possession_style": 0-100, "defensive_line_height": 0-100}
    tactical_profile: dict = field(default_factory=dict)
    # Tactical profile before any in-match (score-state) adjustment, used as
    # the baseline that score-state deltas are applied on top of each tick.
    base_tactical_profile: dict = field(default_factory=dict)
    # Squad members not in the starting lineup, available for substitution
    # (raw player dicts, converted to PlayerState only when subbed on).
    bench: list[dict] = field(default_factory=list)
    subs_made: int = 0
    substitution_profile: dict = field(default_factory=lambda: dict(NEUTRAL_SUBSTITUTION_PROFILE))

    def goalkeeper(self) -> PlayerState:
        return next(p for p in self.lineup if p.slot_position == "GK")

    def outfield(self) -> list[PlayerState]:
        return [p for p in self.lineup if p.slot_position != "GK"]

    def press_intensity(self) -> float:
        return self.tactical_profile.get("press_intensity", 50.0)

    def possession_style(self) -> float:
        return self.tactical_profile.get("possession_style", 50.0)

    def defensive_line_height(self) -> float:
        return self.tactical_profile.get("defensive_line_height", 50.0)

    def chasing_intensity(self) -> float:
        """0-1: how much management.update_score_state_tactics has pushed
        this team's press_intensity *above* its pre-match game-plan
        baseline -- i.e. genuinely chasing a deficit late on, not just
        having a naturally high-press game plan. Protecting a lead pushes
        press_intensity the other way and correctly yields 0 here, not a
        negative value that would otherwise need clamping everywhere this
        is used."""
        current = self.tactical_profile.get("press_intensity", 50.0)
        base = self.base_tactical_profile.get("press_intensity", 50.0)
        return max(0.0, min(1.0, (current - base) / 15.0))


def _mirror_x(x: float) -> float:
    return 100.0 - x


def build_team_state(
    team_id: str,
    players: list[dict],
    formation_name: str,
    attacking_direction: int,
    tactical_profile: dict | None = None,
    substitution_profile: dict | None = None,
) -> TeamState:
    """Assign up to 11 players from `players` (list of player dicts with at
    least id/name/primary_position/secondary_positions/overall/attributes/
    stamina_max) to the slots of the given formation."""
    formation = FORMATIONS[formation_name]
    available = list(players)
    used_ids: set[str] = set()
    assignments: dict[int, dict] = {}

    def pick(slot_idx: int, candidates: list[dict]) -> bool:
        candidates = [p for p in candidates if p["id"] not in used_ids]
        if not candidates:
            return False
        best = max(candidates, key=lambda p: p["overall"])
        assignments[slot_idx] = best
        used_ids.add(best["id"])
        return True

    # Pass 1: exact primary position match.
    for idx, slot in enumerate(formation.slots):
        if idx in assignments:
            continue
        exact = [p for p in available if p["primary_position"] == slot.position]
        pick(idx, exact)

    # Pass 2: alias positions (primary or secondary).
    for idx, slot in enumerate(formation.slots):
        if idx in assignments:
            continue
        aliases = SLOT_POSITION_ALIASES.get(slot.position, [slot.position])
        candidates = [
            p for p in available
            if p["primary_position"] in aliases or any(sp in aliases for sp in p.get("secondary_positions", []))
        ]
        pick(idx, candidates)

    # Pass 3: fallback — any remaining unused player, best overall first.
    for idx, slot in enumerate(formation.slots):
        if idx in assignments:
            continue
        pick(idx, available)

    lineup: list[PlayerState] = []
    for idx, slot in enumerate(formation.slots):
        p = assignments.get(idx)
        if p is None:
            continue
        x, y = slot.x, slot.y
        if attacking_direction == -1:
            x = _mirror_x(x)
        lineup.append(PlayerState(
            player_id=p["id"],
            name=p["name"],
            name_ja=p.get("name_ja"),
            slot_position=slot.position,
            primary_position=p["primary_position"],
            attributes=p["attributes"],
            overall=p["overall"],
            stamina_max=p["stamina_max"],
            current_stamina=float(p["stamina_max"]),
            home_x=x,
            home_y=y,
            x=x,
            y=y,
        ))

    bench = [p for p in available if p["id"] not in used_ids]

    return TeamState(
        team_id=team_id,
        formation=formation,
        lineup=lineup,
        attacking_direction=attacking_direction,
        tactical_profile=dict(tactical_profile or {}),
        base_tactical_profile=dict(tactical_profile or {}),
        bench=bench,
        substitution_profile={**NEUTRAL_SUBSTITUTION_PROFILE, **(substitution_profile or {})},
    )
