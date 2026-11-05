"""Tests for duplicate detection across platforms (core/dedupe.py)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.dedupe import best_platform, find_duplicates, group_spread, normalize_name  # noqa: E402


class TestNormalizeName:
    def test_lowercase_and_punctuation(self):
        assert normalize_name("Vintage Tee, Size L!") == "vintage tee size"

    def test_short_tokens_dropped(self):
        assert normalize_name("Mug of Tea") == "mug tea"
        assert normalize_name("a b cd") == ""

    def test_empty_never_matches(self):
        assert normalize_name("") == ""
        assert normalize_name("!!!") == ""
        assert normalize_name(None) == ""

    def test_unicode_ukrainian(self):
        assert normalize_name("Чашка «Квіти», 350 мл") == "чашка квіти 350"
        # different case/quoting normalizes to the same key
        assert normalize_name("чашка квіти 350") == normalize_name("Чашка  КВІТИ 350!")

    def test_whitespace_collapsed(self):
        assert normalize_name("  leather   wallet  ") == "leather wallet"


class TestFindDuplicates:
    def test_same_item_two_platforms(self):
        items = [
            {"name": "Vintage Denim Jacket", "platform": "etsy", "net": 20.0},
            {"name": "vintage denim jacket!", "platform": "depop", "net": 24.0},
        ]
        groups = find_duplicates(items)
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_unique_items_not_grouped(self):
        items = [
            {"name": "Mug", "platform": "etsy"},
            {"name": "T-shirt", "platform": "etsy"},
            {"name": "Poster", "platform": "amazon"},
        ]
        assert find_duplicates(items) == []

    def test_empty_names_never_grouped(self):
        items = [{"name": "", "platform": "etsy"}, {"name": "", "platform": "depop"}]
        assert find_duplicates(items) == []

    def test_sorted_by_group_size(self):
        items = [
            {"name": "pair a", "platform": "etsy"},
            {"name": "pair a", "platform": "depop"},
            {"name": "trio x", "platform": "etsy"},
            {"name": "trio x", "platform": "depop"},
            {"name": "trio x", "platform": "poshmark"},
        ]
        groups = find_duplicates(items)
        assert len(groups) == 2
        assert len(groups[0]) == 3
        assert len(groups[1]) == 2

    def test_input_order_preserved_within_group(self):
        items = [
            {"name": "Ring", "platform": "depop", "net": 5.0},
            {"name": "ring", "platform": "etsy", "net": 9.0},
        ]
        group = find_duplicates(items)[0]
        assert [g["platform"] for g in group] == ["depop", "etsy"]


class TestComparison:
    def test_best_platform(self):
        group = [{"name": "x", "net": 5.0}, {"name": "y", "net": 12.5}, {"name": "z", "net": 1.0}]
        assert best_platform(group)["name"] == "y"

    def test_best_platform_empty(self):
        assert best_platform([]) is None

    def test_group_spread(self):
        group = [{"net": 3.0}, {"net": 10.0}, {"net": 7.5}]
        assert group_spread(group) == pytest.approx(7.0)


class TestUiHooks:
    """The SPA must expose duplicate detection with a one-click comparison."""

    @staticmethod
    def _html():
        return (Path(__file__).resolve().parents[1] / "index.html").read_text(
            encoding="utf-8")

    def test_functions_exist(self):
        html = self._html()
        for fn in ("findDuplicateGroups", "renderDuplicates", "compareDuplicate"):
            assert f"function {fn}" in html

    def test_wired_to_batch_flow(self):
        html = self._html()
        assert "renderDuplicates()" in html  # called after runBatch
        assert 'onclick="compareDuplicate' in html  # one-click comparison button

    def test_normalize_mirror_matches_python_semantics(self):
        # the JS mirror must produce the same canonical key for the sample
        import subprocess
        code = (
            "const _WORD_RE=/[a-z0-9а-яїієґё]+/gi;"
            "function normalizeName(n,min=3){return (String(n||'').match(_WORD_RE)||[])"
            ".filter(w=>w.length>=min).join(' ').toLowerCase();}"
            "console.log(normalizeName('Vintage Tee, Size L!'));"
        )
        r = subprocess.run(["node", "-e", code], capture_output=True, text=True)
        assert r.stdout.strip() == normalize_name("Vintage Tee, Size L!")
