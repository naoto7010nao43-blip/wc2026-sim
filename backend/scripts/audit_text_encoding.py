"""Audit source/docs text for obvious mojibake artifacts.

This is a deterministic guardrail for UI-facing Japanese copy. It scans
project text files for replacement characters, halfwidth-katakana artifacts,
and known UTF-8/Shift-JIS mojibake markers. Tests may contain marker strings
when they are explicitly asserting that mojibake is absent.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOTS = (
    "frontend/src",
    "backend/app",
    "backend/tests",
    "docs/codex",
    "docs/specs",
    # Japanese name/copy data lives in these seed/report JSON files, and
    # this project has had real mojibake bugs land in data before -- not
    # just source code -- so the guardrail must cover them too.
    "backend/data/seed",
    "backend/reports",
)
TEXT_SUFFIXES = {".css", ".md", ".py", ".ts", ".tsx", ".json"}
MOJIBAKE_MARKERS = ("縺", "繝", "莠", "蜆", "螟", "邇", "謗")


@dataclass(frozen=True)
class EncodingFinding:
    path: str
    line: int
    marker: str
    text: str


def _has_halfwidth_katakana(value: str) -> bool:
    return any(0xFF61 <= ord(ch) <= 0xFF9F for ch in value)


def _allowed_test_marker(line: str) -> bool:
    return (
        "MOJIBAKE_MARKERS" in line
        or "assert_no_mojibake" in line
        or "not in" in line
        or "known mojibake markers" in line
        or "replacement character" in line
    )


def _iter_files(base: Path, roots: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        path = base / root
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            files.append(path)
        elif path.exists():
            files.extend(p for p in path.rglob("*") if p.is_file() and p.suffix in TEXT_SUFFIXES)
    return sorted(files)


def audit_text_encoding(base: Path, roots: tuple[str, ...] = DEFAULT_ROOTS) -> list[EncodingFinding]:
    findings: list[EncodingFinding] = []
    for path in _iter_files(base, roots):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError as exc:
            findings.append(EncodingFinding(path.relative_to(base).as_posix(), 0, "decode-error", str(exc)))
            continue
        for line_no, line in enumerate(lines, start=1):
            if "�" in line:
                if not _allowed_test_marker(line):
                    findings.append(EncodingFinding(path.relative_to(base).as_posix(), line_no, "replacement-character", line.strip()))
            if _has_halfwidth_katakana(line) and not _allowed_test_marker(line):
                findings.append(EncodingFinding(path.relative_to(base).as_posix(), line_no, "halfwidth-katakana", line.strip()))
            for marker in MOJIBAKE_MARKERS:
                if marker in line and not _allowed_test_marker(line):
                    findings.append(EncodingFinding(path.relative_to(base).as_posix(), line_no, marker, line.strip()))
    return findings


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--root", action="append", dest="roots", help="Relative root/file to scan; may be repeated")
    args = parser.parse_args()

    base = Path(args.base).resolve()
    roots = tuple(args.roots) if args.roots else DEFAULT_ROOTS
    findings = audit_text_encoding(base, roots)
    if findings:
        for finding in findings:
            print(f"{finding.path}:{finding.line}: {finding.marker}: {finding.text}")
        return 1
    print("Text encoding audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
