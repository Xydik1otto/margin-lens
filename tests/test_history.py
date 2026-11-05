"""Tests for batch history: margin trend + run summary (core/history.py)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.history import avg_margin, margin_trend, summarize_batch  # noqa: E402


class TestAvgMargin:
    def test_empty(self):
        assert avg_margin([]) == 0.0

    def test_numbers(self):
        assert avg_margin([10.0, 20.0, 30.0]) == pytest.approx(20.0)

    def test_result_dicts(self):
        rows = [{"margin": 12.34}, {"margin": 22.34}, {"margin": 5.32}]
        assert avg_margin(rows) == pytest.approx(13.33)

    def test_missing_margin_counts_as_zero(self):
        assert avg_margin([{"margin": 10.0}, {}]) == pytest.approx(5.0)

    def test_rounded_to_2dp(self):
        assert avg_margin([10.005, 10.005, 10.005]) == pytest.approx(10.01)


class TestMarginTrend:
    def test_empty_history(self):
        t = margin_trend([])
        assert t["direction"] == "none"
        assert t["points"] == []
        assert t["first"] is None and t["last"] is None

    def test_single_run_is_flat(self):
        t = margin_trend([{"ts": 100, "avg_margin": 15.0}])
        assert t["direction"] == "flat"
        assert t["first"] == t["last"] == pytest.approx(15.0)
        assert t["points"] == [(100.0, 15.0)]

    def test_upward_trend(self):
        h = [{"ts": 3, "avg_margin": 20.0}, {"ts": 1, "avg_margin": 10.0},
             {"ts": 2, "avg_margin": 15.0}]
        t = margin_trend(h)
        assert t["direction"] == "up"
        assert t["delta_pp"] == pytest.approx(10.0)
        # sorted chronologically despite out-of-order input
        assert [p[0] for p in t["points"]] == [1.0, 2.0, 3.0]

    def test_downward_trend(self):
        h = [{"ts": 1, "avg_margin": 25.0}, {"ts": 2, "avg_margin": 18.0}]
        t = margin_trend(h)
        assert t["direction"] == "down"
        assert t["delta_pp"] == pytest.approx(-7.0)

    def test_small_change_is_flat(self):
        h = [{"ts": 1, "avg_margin": 15.00}, {"ts": 2, "avg_margin": 15.04}]
        assert margin_trend(h)["direction"] == "flat"
        h2 = [{"ts": 1, "avg_margin": 15.00}, {"ts": 2, "avg_margin": 15.06}]
        assert margin_trend(h2)["direction"] == "up"

    def test_epsilon_threshold_is_inclusive(self):
        h = [{"ts": 1, "avg_margin": 10.0}, {"ts": 2, "avg_margin": 10.05}]
        assert margin_trend(h, eps=0.05)["direction"] == "flat"
        assert margin_trend(h, eps=0.01)["direction"] == "up"

    def test_trend_takes_last_not_max(self):
        # up-down-up sequence: trend compares first vs LAST run
        h = [{"ts": 1, "avg_margin": 10.0}, {"ts": 2, "avg_margin": 30.0},
             {"ts": 3, "avg_margin": 8.0}]
        t = margin_trend(h)
        assert t["direction"] == "down"
        assert t["last"] == pytest.approx(8.0)


class TestSummarizeBatch:
    def test_summary_fields(self):
        rows = [
            {"name": "mug", "platform": "etsy", "net": 10.0, "margin": 25.0},
            {"name": "shirt", "platform": "poshmark", "net": -2.0, "margin": -5.0},
        ]
        s = summarize_batch(rows)
        assert s["count"] == 2
        assert s["avg_margin"] == pytest.approx(10.0)
        assert s["total_net"] == pytest.approx(8.0)
        assert s["best"] == "mug"

    def test_empty_rows(self):
        s = summarize_batch([])
        assert s["count"] == 0 and s["avg_margin"] == 0.0
        assert s["total_net"] == 0.0 and s["best"] is None


class TestUiHooks:
    """The SPA must expose the history feature: new IDB store + functions."""

    @staticmethod
    def _html():
        return (Path(__file__).resolve().parents[1] / "index.html").read_text(
            encoding="utf-8")

    def test_batches_store_registered(self):
        html = self._html()
        assert '"batches"' in html or "'batches'" in html

    def test_save_and_render_functions_exist(self):
        html = self._html()
        for fn in ("saveBatchHistory", "renderBatchHistory", "deleteBatchRun"):
            assert f"function {fn}" in html
        assert "saveBatchHistory()" in html  # wired to a button

    def test_trend_is_rendered(self):
        assert "marginTrendSvg" in self._html()  # sparkline renderer
