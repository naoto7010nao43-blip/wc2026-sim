import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.audit_fifa_squad_list import normalize_name, official_matches_seed, parse_player_line, parse_squad_text


SAMPLE_TEXT = """
Argentina (ARG)
# POS PLAYER NAME FIRST NAME(S) LAST NAME(S) NAME ON SHIRT DOB CLUB HEIGHT (CM) CAPS GOALS
GK MUSSO Juan Juan Agustin MUSSO MUSSO 06/05/1994 Atletico De Madrid (ESP) 193 4 0
FW MESSI Lionel Lionel Andres MESSI MESSI 24/06/1987 Inter Miami CF (USA) 170 200 120
ROLE COACH NAME FIRST NAME(S) LAST NAME(S) NATIONALITY
Head coach SCALONI Lionel Lionel Sebastian SCALONI Argentina
DOB Date of birth POS Position GK Goalkeeper DF Defender MF Midelder FW Forward
SQUAD LISTBrazil (BRA)
# POS PLAYER NAME FIRST NAME(S) LAST NAME(S) NAME ON SHIRT DOB CLUB HEIGHT (CM) CAPS GOALS
GK ALISSON Alisson Ramses BECKER ALISSON 02/10/1992 Liverpool FC (ENG) 193 80 0
FW VINICIUS JUNIOR Vinicius Jose Paixao DE OLIVEIRA JUNIOR VINI JR 12/07/2000 Real Madrid C. F. (ESP) 176 42 7
ROLE COACH NAME FIRST NAME(S) LAST NAME(S) NATIONALITY
Head coach ANCELOTTI Carlo Carlo ANCELOTTI Italy
"""


def test_normalize_name_removes_accents_and_punctuation():
    assert normalize_name("Julián Álvarez") == "julianalvarez"
    assert normalize_name("Vinícius Júnior") == "viniciusjunior"
    assert normalize_name("N. González") == "ngonzalez"


def test_parse_squad_text_extracts_teams_players_and_coaches():
    teams = parse_squad_text(SAMPLE_TEXT)
    assert set(teams) == {"ARG", "BRA"}
    assert teams["ARG"].team_name == "Argentina"
    assert teams["ARG"].players[1].position == "FW"
    assert teams["ARG"].players[1].caps == 200
    assert teams["ARG"].players[1].goals == 120
    assert teams["ARG"].coach_name_block == "SCALONI Lionel Lionel Sebastian SCALONI"
    assert teams["BRA"].players[0].club == "Liverpool FC (ENG)"
    assert teams["BRA"].coach_nationality == "Italy"


def test_official_matches_seed_tolerates_pdf_name_order():
    assert official_matches_seed("Carlo Ancelotti", "ANCELOTTI Carlo Carlo ANCELOTTI")
    assert official_matches_seed("Alisson Becker", "ALISSON Alisson Ramses BECKER ALISSON")


def test_parse_player_line_handles_pypdf_compacted_columns():
    player = parse_player_line("FWMESSI LionelLionel Andres MESSI MESSI 24/06/1987Inter Miami CF (USA) 170 200120")
    assert player is not None
    assert player.position == "FW"
    assert player.dob == "24/06/1987"
    assert player.club == "Inter Miami CF (USA)"
    assert player.height_cm == 170
    assert player.caps == 200
    assert player.goals == 120
