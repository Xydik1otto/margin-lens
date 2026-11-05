"""Тести порівняння з цільовою маржею (core/target_margin.py)."""

import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.fees import FeeInputs, calculate  # noqa: E402
from core.target_margin import (  # noqa: E402
    gap_to_target,
    price_for_target_margin,
    target_report,
)


def inp(**kw) -> FeeInputs:
    base = dict(platform="etsy", price=30.0, product_cost=8.0,
                shipping_paid=4.0, shipping_charged=5.0)
    base.update(kw)
    return FeeInputs(**base)


# Etsy-база: revenue 35, pct 0.095, fixed 0.45 -> net 19.23, margin 54.93%
EXPECTED_ETSY_MARGIN = 54.93


class TestGapToTarget:
    def test_above_target(self):
        g = gap_to_target(EXPECTED_ETSY_MARGIN, 50.0)
        assert g["status"] == "above"
        assert g["gap_pp"] == pytest.approx(4.93, abs=0.01)
        assert g["target"] == 50.0

    def test_on_target_within_eps(self):
        assert gap_to_target(30.02, 30.0)["status"] == "on"
        assert gap_to_target(29.96, 30.0)["status"] == "on"

    def test_below_target(self):
        g = gap_to_target(20.0, 30.0)
        assert g["status"] == "below"
        assert g["gap_pp"] == pytest.approx(-10.0)

    def test_no_target_set(self):
        for target in (None, 0, -5):
            g = gap_to_target(EXPECTED_ETSY_MARGIN, target)
            assert g["status"] == "none"
            assert g["target"] is None
            assert g["gap_pp"] is None

    def test_gap_matches_calculate_margin(self):
        res = calculate(inp())
        g = gap_to_target(res.margin_pct, 40.0)
        assert g["actual"] == res.margin_pct
        assert g["gap_pp"] == pytest.approx(res.margin_pct - 40.0, abs=0.011)


class TestPriceForTargetMargin:
    @pytest.mark.parametrize("target", [20.0, 30.0, 40.0, 50.0])
    def test_roundtrip_margin_hits_target(self, target):
        p = price_for_target_margin(inp(), target)
        assert p is not None
        res = calculate(replace(inp(), price=p))
        assert res.margin_pct == pytest.approx(target, abs=0.3)

    def test_exact_etsy_solution(self):
        # denom = 1 - 0.095 - 0.40 = 0.505; need = 8 + 4 + 0.45 = 12.45
        # P = 12.45/0.505 - 5 = 19.65
        assert price_for_target_margin(inp(), 40.0) == pytest.approx(19.65)

    def test_target_zero_or_none(self):
        assert price_for_target_margin(inp(), 0) is None
        assert price_for_target_margin(inp(), -10) is None

    def test_target_unreachable(self):
        # pct 0.095 + vat 0.60 + target 0.50 > 1 -> жодна ціна не дає 50%
        assert price_for_target_margin(inp(vat_percent=60.0), 50.0) is None

    def test_higher_target_needs_higher_price(self):
        p30 = price_for_target_margin(inp(), 30.0)
        p50 = price_for_target_margin(inp(), 50.0)
        assert p50 > p30

    def test_vat_included_in_pct_total(self):
        # з VAT 20% ціна для тієї ж цілі має бути вищою
        p_no_vat = price_for_target_margin(inp(), 40.0)
        p_vat = price_for_target_margin(inp(vat_percent=20.0), 40.0)
        assert p_vat > p_no_vat

    def test_multiplies_fixed_by_units(self):
        # 2 од. у замовленні: listing 0.40 замість 0.20 -> вища ціна
        p1 = price_for_target_margin(inp(), 40.0)
        p2 = price_for_target_margin(inp(units=2), 40.0)
        assert p2 > p1


class TestPoshmark:
    def test_flat_tier_roundtrip(self):
        # ціна 10, собівартість 2: margin (10 - 2.95 - 2) / 10 = 50.5%
        base = inp(platform="poshmark", price=10.0, product_cost=2.0,
                   shipping_paid=0.0, shipping_charged=0.0)
        assert calculate(base).margin_pct == pytest.approx(50.5, abs=0.01)
        p = price_for_target_margin(base, 40.0)
        assert p < 15.0  # лишається в flat-рівні
        assert calculate(replace(base, price=p)).margin_pct == pytest.approx(40.0, abs=0.3)

    def test_pct_tier_roundtrip(self):
        base = inp(platform="poshmark", price=20.0, product_cost=12.0,
                   shipping_paid=0.0, shipping_charged=0.0)
        p = price_for_target_margin(base, 5.0)
        assert p >= 15.0  # 20% рівень
        assert calculate(replace(base, price=p)).margin_pct == pytest.approx(5.0, abs=0.3)

    def test_target_crosses_into_pct_tier(self):
        # ціль 5% при cost 12: flat-рівень дав би ціну нижче межі… розв'язок
        # має взяти узгоджений рівень
        base = inp(platform="poshmark", price=20.0, product_cost=12.0,
                   shipping_paid=0.0, shipping_charged=0.0)
        p = price_for_target_margin(base, 5.0)
        assert p == pytest.approx(16.0, abs=0.02)

    def test_unreachable_pct_tier(self):
        # vat 60% + 20% + target 30% > 100% -> None
        base = inp(platform="poshmark", price=20.0, product_cost=5.0,
                   vat_percent=60.0)
        assert price_for_target_margin(base, 30.0) is None


class TestTargetReport:
    def test_report_shape(self):
        r = target_report(inp(), 50.0)
        assert set(r) == {"actual", "target", "gap_pp", "status", "price_needed"}
        assert r["actual"] == EXPECTED_ETSY_MARGIN
        assert r["status"] == "above"
        assert r["price_needed"] is not None

    def test_report_without_target(self):
        r = target_report(inp(), None)
        assert r["status"] == "none"
        assert r["price_needed"] is None
