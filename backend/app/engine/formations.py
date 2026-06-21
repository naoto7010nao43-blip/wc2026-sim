"""Static formation definitions: 11 slots with base pitch coordinates.

x: 0 (own goal) - 100 (opponent goal); y: 0-100 (touchline to touchline).
These are the attacking-direction-normalized coordinates for the team
attacking toward x=100; they get mirrored for the away team in state.py.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FormationSlot:
    position: str
    x: float
    y: float


@dataclass(frozen=True)
class Formation:
    name: str
    slots: tuple[FormationSlot, ...]


FORMATIONS: dict[str, Formation] = {
    "4-3-3": Formation(
        name="4-3-3",
        slots=(
            FormationSlot("GK", 5, 50),
            FormationSlot("LB", 25, 15),
            FormationSlot("CB", 18, 38),
            FormationSlot("CB", 18, 62),
            FormationSlot("RB", 25, 85),
            FormationSlot("CDM", 42, 50),
            FormationSlot("CM", 52, 30),
            FormationSlot("CM", 52, 70),
            FormationSlot("LW", 75, 15),
            FormationSlot("ST", 82, 50),
            FormationSlot("RW", 75, 85),
        ),
    ),
    "4-2-3-1": Formation(
        name="4-2-3-1",
        slots=(
            FormationSlot("GK", 5, 50),
            FormationSlot("LB", 25, 15),
            FormationSlot("CB", 18, 38),
            FormationSlot("CB", 18, 62),
            FormationSlot("RB", 25, 85),
            FormationSlot("CDM", 40, 35),
            FormationSlot("CDM", 40, 65),
            FormationSlot("LW", 68, 15),
            FormationSlot("CAM", 65, 50),
            FormationSlot("RW", 68, 85),
            FormationSlot("ST", 85, 50),
        ),
    ),
    "4-4-2": Formation(
        name="4-4-2",
        slots=(
            FormationSlot("GK", 5, 50),
            FormationSlot("LB", 25, 15),
            FormationSlot("CB", 18, 38),
            FormationSlot("CB", 18, 62),
            FormationSlot("RB", 25, 85),
            FormationSlot("LM", 55, 15),
            FormationSlot("CM", 48, 38),
            FormationSlot("CM", 48, 62),
            FormationSlot("RM", 55, 85),
            FormationSlot("ST", 80, 38),
            FormationSlot("ST", 80, 62),
        ),
    ),
    "3-5-2": Formation(
        name="3-5-2",
        slots=(
            FormationSlot("GK", 5, 50),
            FormationSlot("CB", 18, 25),
            FormationSlot("CB", 15, 50),
            FormationSlot("CB", 18, 75),
            FormationSlot("LM", 50, 10),
            FormationSlot("CDM", 38, 38),
            FormationSlot("CM", 48, 50),
            FormationSlot("CDM", 38, 62),
            FormationSlot("RM", 50, 90),
            FormationSlot("ST", 80, 38),
            FormationSlot("ST", 80, 62),
        ),
    ),
    # Back-three with advanced wing-backs and a double pivot behind two
    # attacking mids -- added when the real-formation research pass found
    # several 2026 national teams (USA, AUS, CZE, etc.) actually playing
    # this rather than any of the 4 templates above.
    "3-4-2-1": Formation(
        name="3-4-2-1",
        slots=(
            FormationSlot("GK", 5, 50),
            FormationSlot("CB", 15, 30),
            FormationSlot("CB", 12, 50),
            FormationSlot("CB", 15, 70),
            FormationSlot("LB", 45, 8),
            FormationSlot("RB", 45, 92),
            FormationSlot("CDM", 40, 40),
            FormationSlot("CM", 45, 60),
            FormationSlot("CAM", 68, 30),
            FormationSlot("CAM", 68, 70),
            FormationSlot("ST", 88, 50),
        ),
    ),
    # Back-three with a flat four across midfield and a front three --
    # added for the same reason as 3-4-2-1 (SWE, JOR, CUW, COD, etc.).
    "3-4-3": Formation(
        name="3-4-3",
        slots=(
            FormationSlot("GK", 5, 50),
            FormationSlot("CB", 15, 30),
            FormationSlot("CB", 12, 50),
            FormationSlot("CB", 15, 70),
            FormationSlot("LM", 50, 12),
            FormationSlot("CM", 45, 38),
            FormationSlot("CM", 45, 62),
            FormationSlot("RM", 50, 88),
            FormationSlot("LW", 78, 15),
            FormationSlot("ST", 85, 50),
            FormationSlot("RW", 78, 85),
        ),
    ),
}

# Maps a formation slot's generic position label to acceptable player
# primary/secondary position codes, used when assigning real players to slots.
SLOT_POSITION_ALIASES: dict[str, list[str]] = {
    "GK": ["GK"],
    "CB": ["CB"],
    "LB": ["LB", "CB"],
    "RB": ["RB", "CB"],
    "CDM": ["CDM", "CM"],
    "CM": ["CM", "CDM", "CAM"],
    "CAM": ["CAM", "CM"],
    "LM": ["LM", "LW", "CM"],
    "RM": ["RM", "RW", "CM"],
    "LW": ["LW", "LM"],
    "RW": ["RW", "RM"],
    "ST": ["ST", "CAM"],
}
