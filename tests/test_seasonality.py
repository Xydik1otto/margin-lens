"""Тести сезонності продажів (core/seasonality.py)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.seasonality import (  # noqa: E402
    MONTHS_EN,
    MONTHS_UA,
    SEASONALITY,
    peak_months,
    quiet_months,
    seasonality_factor,
    seasonality_level,
    seasonality_note,
)


class TestDataIntegrity:
    def test_each_category_has_12_factors(self):
        for key, cat in SEASONALITY.items():
            assert len(cat["factors"]) == 12, key
            for f in cat["factors"]:
                assert 0.2 <= f <= 2.5, (key, f)

    def test_labels_ua_and_en(self):
        for key, cat in SEASONALITY.items():
            assert cat["label"].strip(), key
            assert cat["label_en"].strip(), key

    def test_data_sanity_peak_and_quiet_exist(self):
        # кожна ніша має і пік (планування запасів), і спад (період підготовки)
        for key in SEASONALITY:
            assert peak_months(key), key
            assert quiet_months(key), key

    def test_month_names(self):
        assert len(MONTHS_UA) == len(MONTHS_EN) == 12
        assert MONTHS_UA[11] == "Грудень"
        assert MONTHS_EN[0] == "January"


class TestFactor:
    def test_known_values(self):
        # Різдвяний декор: грудень 1.6, листопад 2.0, січень 0.3
        assert seasonality_factor("christmas_decor", 12) == 1.6
        assert seasonality_factor("christmas_decor", 11) == 2.0
        assert seasonality_factor("christmas_decor", 1) == 0.3

    def test_unknown_category_raises(self):
        with pytest.raises(KeyError):
            seasonality_factor("no_such_niche", 5)

    @pytest.mark.parametrize("month", [0, 13, -1])
    def test_month_out_of_range_raises(self, month):
        with pytest.raises(ValueError):
            seasonality_factor("apparel", month)


class TestLevel:
    @pytest.mark.parametrize("factor,expected", [
        (1.3, "peak"), (2.2, "peak"),
        (1.2, "high"), (1.1, "high"),
        (1.05, "normal"), (0.9, "normal"),
        (0.8, "low"), (0.3, "low"),
    ])
    def test_thresholds(self, factor, expected):
        assert seasonality_level(factor) == expected


class TestPeakQuiet:
    def test_christmas_peaks(self):
        assert peak_months("christmas_decor") == [10, 11, 12]

    def test_toys_peak_q4(self):
        assert peak_months("toys_kids") == [11, 12]

    def test_wedding_peaks_summer(self):
        assert peak_months("wedding") == [4, 5, 6, 7, 8]

    def test_christmas_quiet_includes_january(self):
        assert 1 in quiet_months("christmas_decor")


class TestNote:
    def test_note_shape_and_factor(self):
        n = seasonality_note("christmas_decor", 11)
        assert n["month"] == 11
        assert n["month_name_ua"] == "Листопад"
        assert n["month_name_en"] == "November"
        assert n["factor"] == 2.0
        assert n["level"] == "peak"
        assert "Листопад" in n["note"] and "2.00" in n["note"]

    def test_note_en(self):
        n = seasonality_note("toys_kids", 12, lang="en")
        assert n["note"].startswith("December is a peak month")
        assert "×2.20" in n["note"]

    def test_note_levels_cover_all(self):
        for key in SEASONALITY:
            for m in range(1, 13):
                n = seasonality_note(key, m)
                assert n["note"].strip()
                assert n["level"] in ("peak", "high", "normal", "low")

    def test_unknown_lang_falls_back_to_ua(self):
        n = seasonality_note("apparel", 3, lang="de")
        assert n["note"].startswith("Березень")
