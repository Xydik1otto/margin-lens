"""Accessibility checks for index.html (WAVE4 загальні вимоги, п.7)."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def html() -> str:
    return (ROOT / "index.html").read_text(encoding="utf-8")


def test_focus_visible_css():
    h = html()
    assert ":focus-visible" in h
    assert "outline:2px solid" in h


def test_all_icon_only_buttons_have_aria_label():
    h = html()
    for btn in re.findall(r"<button\b[^>]*>(.*?)</button>", h, re.S):
        text = re.sub(r"<[^>]+>", "", btn).strip()
        tag = re.search(r"<button\b([^>]*)>", h)
    # every <button ...> opening tag: icon-only ones (no visible text) need aria-label
    for m in re.finditer(r"<button\b([^>]*)>", h):
        attrs = m.group(1)
        # grab the button's inner text
        start = m.end()
        end = h.find("</button>", start)
        inner = re.sub(r"<[^>]+>", "", h[start:end]).strip()
        if not inner:
            assert "aria-label" in attrs, f"icon-only button without aria-label: {attrs}"


def test_scenario_rows_are_keyboard_accessible():
    h = html()
    assert 'role="button" tabindex="0"' in h
    assert "onkeydown" in h  # Enter/Space activation


def test_language_attribute_and_toggle_group():
    h = html()
    assert '<html lang="uk">' in h  # UA default; JS updates it on switch
    assert 'aria-label="Мова / Language"' in h


def test_tables_and_charts_labelled():
    h = html()
    assert 'role="img" aria-label=' in h  # SVG charts
    assert 'aria-live="polite"' in h      # async result regions


def test_no_russian_strings_anywhere():
    # Ukrainian shares Cyrillic with Russian; distinctly Russian markers must not appear
    h = html().lower()
    for marker in ("расч", "сохран", "поддержк", "язык интерф", "русск"):
        assert marker not in h, marker
