"""Tests for Markdown table export (core/md_export.py)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.md_export import (  # noqa: E402
    batch_results_markdown,
    compare_results_markdown,
    md_escape,
    markdown_table,
)


class TestMdEscape:
    def test_pipes_escaped(self):
        assert md_escape("a|b") == "a\\|b"

    def test_newlines_flattened(self):
        assert md_escape("line1\nline2") == "line1 line2"

    def test_plain_text_untouched(self):
        assert md_escape("net profit $12.50") == "net profit $12.50"


class TestMarkdownTable:
    def test_basic_shape(self):
        out = markdown_table(["A", "B"], [[1, 2], [3, 4]])
        lines = out.splitlines()
        assert lines[0] == "| A | B |"
        assert lines[1] == "|---|---|"
        assert lines[2] == "| 1 | 2 |"
        assert lines[3] == "| 3 | 4 |"

    def test_empty_rows_still_valid(self):
        out = markdown_table(["A"], [])
        assert out.splitlines() == ["| A |", "|---|"]

    def test_pipe_in_cell_does_not_break_columns(self):
        import re
        out = markdown_table(["Name"], [["a|b"]])
        body = out.splitlines()[2]
        # split on unescaped pipes only -> exactly one data column
        cols = re.split(r"(?<!\\)\|", body)
        assert [c.strip() for c in cols if c.strip()] == ["a\\|b"]


class TestBatchMarkdown:
    def test_rows_rendered(self):
        rows = [
            {"name": "mug", "platform": "etsy", "revenue": 35.0, "fees": 5.25,
             "net": 17.75, "margin": 50.71},
        ]
        out = batch_results_markdown(rows)
        assert "## Margin Lens — результати" in out
        assert "| mug | etsy | 35.00 | 5.25 | 17.75 | 50.7 |" in out

    def test_pipe_in_product_name(self):
        rows = [{"name": "cup | saucer", "platform": "etsy", "revenue": 1,
                 "fees": 0, "net": 1, "margin": 100}]
        out = batch_results_markdown(rows)
        assert "cup \\| saucer" in out

    def test_empty_rows(self):
        out = batch_results_markdown([])
        assert out.splitlines()[0].startswith("## Margin Lens")


class TestCompareMarkdown:
    def test_rows_and_breakeven_dash(self):
        rows = [
            {"platform": "etsy", "fees": 2.48, "vat": 0, "net": 20.52,
             "margin": 58.63, "breakeven": 14.5},
            {"platform": "vinted", "fees": 0, "vat": 0, "net": 23.0,
             "margin": 65.71, "breakeven": None},
        ]
        out = compare_results_markdown(rows)
        assert "| etsy | 2.48 | 0.00 | 20.52 | 58.63 | 14.50 |" in out
        assert "| vinted | 0.00 | 0.00 | 23.00 | 65.71 | — |" in out


class TestUiHooks:
    """The SPA must offer one-click Markdown copy."""

    @staticmethod
    def _html():
        return (Path(__file__).resolve().parents[1] / "index.html").read_text(
            encoding="utf-8")

    def test_copy_functions_exist(self):
        html = self._html()
        for fn in ("copyBatchMarkdown", "copyCompareMarkdown", "copyToClipboard"):
            assert f"function {fn}" in html

    def test_wired_to_buttons(self):
        html = self._html()
        assert "copyBatchMarkdown()" in html
        assert "copyCompareMarkdown()" in html
