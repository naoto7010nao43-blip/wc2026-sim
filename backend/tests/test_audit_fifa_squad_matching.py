import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.audit_fifa_squad_list import (  # noqa: E402
    compact_name_candidates,
    meaningful_name_tokens,
    official_matches_seed,
)


def test_official_matches_seed_handles_glued_repeated_display_names():
    assert official_matches_seed(
        "Christian Pulisic",
        "PULISIC ChristianChristian MatePULISIC PULISIC",
    )
    assert official_matches_seed(
        "Jude Bellingham",
        "BELLINGHAM JudeJude Victor William BELLINGHAM BELLINGHAM",
    )


def test_official_matches_seed_handles_surname_first_and_particles():
    assert official_matches_seed(
        "Rodrigo De Paul",
        "DE PAUL RodrigoRodrigo Javier DE PAUL DE PAUL",
    )
    assert official_matches_seed(
        "Leo Skiri Ostigard",
        "OSTIGARD LeoLeo Skiri OSTIGARDOSTIGARD",
    )


def test_official_matches_seed_handles_apostrophes_and_hyphens():
    assert official_matches_seed(
        "Nico OReilly",
        "OREILLY Nico Nico O'REILLY O'REILLY",
    )
    assert official_matches_seed(
        "Warren Zaire-Emery",
        "ZAIRE-EMERY Warren Warren Marie Jean-Pierre ZAIRE-EMERY ZAIRE-EMERY",
    )


def test_official_matches_seed_handles_diacritics():
    assert official_matches_seed(
        "Nicolas Tagliafico",
        "TAGLIAFICO Nicol\u00e1s Alejandro TAGLIAFICO TAGLIAFICO",
    )


def test_official_matches_seed_handles_suffix_tokens_conservatively():
    assert official_matches_seed(
        "Derrick Etienne Jr.",
        "ETIENNE DerrickDerrick Burckley ETIENNE JRETIENNE JR",
    )


def test_official_matches_seed_does_not_match_one_shared_common_token():
    assert not official_matches_seed(
        "James Rodriguez",
        "CORDOBA Jhon Janer Lucumi CORDOBA J. CORDOBA",
    )
    assert not official_matches_seed(
        "David Silva",
        "DAVID JonathanJonathan ChristianDAVID J. DAVID",
    )


def test_meaningful_name_tokens_drop_particles_and_dedupe():
    assert meaningful_name_tokens("Rodrigo De Paul Paul") == ["rodrigo", "paul"]
    assert meaningful_name_tokens("Roshon van Eijma") == ["roshon", "eijma"]


def test_compact_name_candidates_include_order_variants():
    candidates = compact_name_candidates("Christian Pulisic")
    assert "christianpulisic" in candidates
    assert "pulisicchristian" in candidates
