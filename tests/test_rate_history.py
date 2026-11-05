"""Тести історії змін тарифів (core/rate_history.py)."""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.rate_history import (  # noqa: E402
    PLATFORMS,
    RATE_HISTORY,
    changes_for,
    format_changes,
    last_change,
    platforms_with_history,
    platforms_without_history,
)

# Платформи, які реально модельує core/fees.py (джерело правди).
FEES_PLATFORMS = {"etsy", "shopify", "amazon", "ebay", "vinted", "depop", "poshmark"}


class TestDataIntegrity:
    def test_dates_are_iso(self):
        for e in RATE_HISTORY:
            assert date.fromisoformat(e["date"]), e

    def test_dates_not_in_future(self):
        for e in RATE_HISTORY:
            assert date.fromisoformat(e["date"]) <= date.today(), e

    def test_platforms_are_known(self):
        for e in RATE_HISTORY:
            assert e["platform"] in FEES_PLATFORMS, e

    def test_journal_covers_only_modeled_platforms(self):
        assert set(PLATFORMS) == FEES_PLATFORMS
        for e in RATE_HISTORY:
            assert e["platform"] in PLATFORMS

    def test_ua_and_en_texts_nonempty(self):
        for e in RATE_HISTORY:
            assert e["ua"].strip(), e
            assert e["en"].strip(), e

    def test_no_duplicate_date_platform_pairs(self):
        pairs = [(e["date"], e["platform"]) for e in RATE_HISTORY]
        assert len(pairs) == len(set(pairs))

    def test_no_russian_text(self):
        for e in RATE_HISTORY:
            for marker in ("Расч", "сохран", " ы ", "ъ", "русск"):
                assert marker not in e["ua"], (e, marker)


class TestQueries:
    def test_changes_for_sorted_desc(self):
        entries = changes_for("etsy")
        dates = [e["date"] for e in entries]
        assert dates == sorted(dates, reverse=True)
        assert len(dates) >= 2

    def test_changes_for_unknown_platform_raises(self):
        with pytest.raises(ValueError):
            changes_for("aliexpress")

    def test_last_change(self):
        lc = last_change("etsy")
        assert lc is not None and lc["date"] == "2023-06-01"
        assert last_change("vinted") is None
        assert last_change("shopify") is None

    def test_platforms_with_without_history_partition(self):
        with_h = platforms_with_history()
        without_h = platforms_without_history()
        assert set(with_h) | set(without_h) == FEES_PLATFORMS
        assert not set(with_h) & set(without_h)
        assert "etsy" in with_h and "depop" in with_h

    def test_depop_us_fee_removal_recorded(self):
        entries = changes_for("depop")
        assert any("10%" in e["ua"] and e["date"] == "2024-07-15" for e in entries)


class TestFormat:
    def test_format_for_platform(self):
        lines = format_changes("ebay")
        assert len(lines) == 1
        assert lines[0].startswith("2023-02-15 — ")
        assert "13.25%" in lines[0]

    def test_format_all_sorted_desc_with_platform_tag(self):
        lines = format_changes()
        dates = [ln.split(" ")[0] for ln in lines]
        assert dates == sorted(dates, reverse=True)
        for ln in lines:
            assert "[" in ln and "]" in ln

    def test_format_en(self):
        lines = format_changes("etsy", lang="en")
        assert all(ln for ln in lines)
        assert any("6.5%" in ln for ln in lines)
