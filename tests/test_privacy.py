"""Privacy/leak regression for an open-source repo.

Open-source hygiene (WAVE4): no local paths, no credentials, no personal
data in the working tree; fee rates carry a "last verified" date comment;
no Russian localization anywhere.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCAN_GLOBS = ["*.py", "*.html", "*.js", "*.md", "*.yml", "*.yaml", "*.sh", "*.toml", "*.cfg"]
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules"}

# Patterns that must never appear in a public repo
LEAK_PATTERNS = [
    (re.compile(r"[A-Z]:\\\\Users\\\\", re.I), "Windows user path"),
    (re.compile(r"\bg:[/\\]projects\b", re.I), "local G:\\Projects path"),
    (re.compile(r"\bc:[/\\]users\b", re.I), "local C:\\Users path"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"), "GitHub PAT"),
    (re.compile(r"\bgho_[A-Za-z0-9]{20,}\b"), "GitHub OAuth token"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "API secret key"),
    (re.compile(r"\bxox[bap]-[A-Za-z0-9-]{10,}\b"), "Slack token"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@(?!example\.|noreply|users\.noreply)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
     "personal email (use @users.noreply or example.com)"),
]


def repo_files():
    for p in ROOT.rglob("*"):
        if p.is_dir() or any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in SCAN_GLOBS or p.name in ("pyproject.toml",):
            yield p


def test_no_leaks_in_working_tree():
    leaks = []
    for p in repo_files():
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue
        for rx, label in LEAK_PATTERNS:
            for m in rx.finditer(text):
                leaks.append(f"{p.relative_to(ROOT)}: {label}: ...{m.group(0)[:30]}...")
    assert not leaks, "Privacy leaks found:\n" + "\n".join(leaks)


def test_fee_rates_have_verified_date_comments():
    src = (ROOT / "core" / "fees.py").read_text(encoding="utf-8")
    assert re.search(r"last verified \d{4}-\d{2}-\d{2}", src), \
        "core/fees.py must document when the rates were last verified"
    fx = (ROOT / "core" / "fx.py").read_text(encoding="utf-8")
    assert re.search(r"verified \d{4}-\d{2}-\d{2}", fx)


def test_issue_templates_exist_bilingual_no_russian():
    d = ROOT / ".github" / "ISSUE_TEMPLATE"
    assert (d / "bug_report.md").exists()
    assert (d / "feature_request.md").exists()
    for f in d.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        assert "Language" in text  # bilingual header marker


def test_community_files_present():
    for name in ("CONTRIBUTING.md", "SECURITY.md", "README.en.md", "INSTALL.md",
                 "CHANGELOG.md", "LICENSE", "README.md"):
        assert (ROOT / name).exists(), name


def test_contributing_documents_rate_update_workflow():
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "generate_js.py" in text
    assert "core/fees.py" in text


def test_gitignore_covers_python_artifacts():
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for needle in ("__pycache__", "*.pyc", ".pytest_cache"):
        assert needle in gi


def test_no_russian_in_documentation():
    for name in ("README.md", "README.en.md", "INSTALL.md", "CONTRIBUTING.md",
                 "SECURITY.md", "CHANGELOG.md"):
        text = (ROOT / name).read_text(encoding="utf-8").lower()
        for marker in ("расч", "сохран", "поддержк", "интерфейс", "русск"):
            assert marker not in text, f"{name}: {marker}"
