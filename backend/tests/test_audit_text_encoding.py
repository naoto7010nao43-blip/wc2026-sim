import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from audit_text_encoding import DEFAULT_ROOTS, audit_text_encoding


def test_audit_text_encoding_passes_clean_files(tmp_path):
    src = tmp_path / "frontend" / "src"
    src.mkdir(parents=True)
    (src / "Clean.tsx").write_text('export const label = "大会モード";\n', encoding="utf-8")

    findings = audit_text_encoding(tmp_path, ("frontend/src",))

    assert findings == []


def test_audit_text_encoding_flags_mojibake(tmp_path):
    src = tmp_path / "frontend" / "src"
    src.mkdir(parents=True)
    broken = chr(0x7E5D) + chr(0xFF62)
    (src / "Broken.tsx").write_text(f'export const label = "{broken}";\n', encoding="utf-8")

    findings = audit_text_encoding(tmp_path, ("frontend/src",))

    assert findings
    assert findings[0].path == "frontend/src/Broken.tsx"


def test_audit_text_encoding_allows_marker_regression_tests(tmp_path):
    tests = tmp_path / "backend" / "tests"
    tests.mkdir(parents=True)
    marker = chr(0x7E3A)
    (tests / "test_example.py").write_text(f'assert "{marker}" not in text\n', encoding="utf-8")

    findings = audit_text_encoding(tmp_path, ("backend/tests",))

    assert findings == []


def test_audit_text_encoding_covers_seed_and_report_json_data():
    # Japanese name/copy data lives in JSON, not just source code, and this
    # project has had real mojibake bugs land in data before -- the
    # guardrail must scan it, not only frontend/backend source files.
    assert "backend/scripts" in DEFAULT_ROOTS
    assert "backend/data/seed" in DEFAULT_ROOTS
    assert "backend/reports" in DEFAULT_ROOTS


def test_audit_text_encoding_flags_mojibake_in_seed_json(tmp_path):
    seed = tmp_path / "backend" / "data" / "seed"
    seed.mkdir(parents=True)
    broken = chr(0x7E5D) + chr(0xFF62)
    (seed / "players.json").write_text(f'[{{"name_ja": "{broken}"}}]', encoding="utf-8")

    findings = audit_text_encoding(tmp_path, ("backend/data/seed",))

    assert findings
    assert findings[0].path == "backend/data/seed/players.json"
