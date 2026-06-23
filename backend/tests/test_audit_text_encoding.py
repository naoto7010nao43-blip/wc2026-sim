import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from audit_text_encoding import audit_text_encoding


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
    (tests / "test_example.py").write_text('assert "縺" not in text\n', encoding="utf-8")

    findings = audit_text_encoding(tmp_path, ("backend/tests",))

    assert findings == []
