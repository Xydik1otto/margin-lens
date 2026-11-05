"""Tests for Depop (10% marketplace fee) and Poshmark ($2.95 flat under $15,
20% over) fee structures."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.fees import (  # noqa: E402
    DEPOP,
    POSHMARK,
    POSHMARK_FLAT_UNDER,
    FeeInputs,
    breakeven_price,
    calculate,
    depop_fees,
    poshmark_fees,
)
from core.fx import reset_rates  # noqa: E402


@pytest.fixture(autouse=True)
def _fallback_rates():
    reset_rates()
    yield
    reset_rates()


def m(**kw):
    defaults = dict(platform="etsy", price=30.0, product_cost=8.0,
                    shipping_paid=4.0, shipping_charged=5.0)
    defaults.update(kw)
    return FeeInputs(**defaults)


class TestDepop:
    def test_constants(self):
        assert DEPOP["marketplace_pct"] == pytest.approx(0.10)

    def test_fee_is_10pct_of_total_sale(self):
        # base = 30 + 5 = 35 -> 10% = 3.50
        fees = depop_fees(m(platform="depop"))
        assert fees["marketplace"] == pytest.approx(3.50)

    def test_fee_includes_shipping_charged(self):
        fees = depop_fees(m(platform="depop", shipping_charged=0.0))
        assert fees["marketplace"] == pytest.approx(3.00)

    def test_net_profit(self):
        # net = 35 - 3.50 - 8 - 4 = 19.50
        r = calculate(m(platform="depop"))
        assert r.total_fees == pytest.approx(3.50)
        assert r.net_profit == pytest.approx(19.50, abs=0.01)
        assert r.margin_pct == pytest.approx(19.50 / 35 * 100, abs=0.01)

    def test_units_do_not_multiply_pct_fee(self):
        fees = depop_fees(m(platform="depop", units=3))
        assert fees["marketplace"] == pytest.approx(3.50)

    def test_breakeven(self):
        # pct = 0.10; fixed = 0; need = 8 + 4 = 12
        # total = 12 / 0.9 = 13.333; price = 13.333 - 5 = 8.33
        assert breakeven_price(m(platform="depop")) == pytest.approx(8.33, abs=0.01)

    def test_breakeven_zero_net_roundtrip(self):
        be = breakeven_price(m(platform="depop"))
        r = calculate(m(platform="depop", price=be))
        assert r.net_profit == pytest.approx(0.0, abs=0.02)

    def test_vat_applies(self):
        r = calculate(m(platform="depop", vat_percent=20))
        assert r.vat == pytest.approx(0.20 * 35)


class TestPoshmark:
    def test_constants(self):
        assert POSHMARK["flat_fee_under"] == pytest.approx(2.95)
        assert POSHMARK["pct_over"] == pytest.approx(0.20)
        assert POSHMARK_FLAT_UNDER == pytest.approx(15.0)

    def test_flat_fee_under_15(self):
        fees = poshmark_fees(m(platform="poshmark", price=14.99))
        assert fees["commission"] == pytest.approx(2.95)

    def test_pct_fee_at_15(self):
        fees = poshmark_fees(m(platform="poshmark", price=15.00))
        assert fees["commission"] == pytest.approx(3.00)

    def test_pct_fee_over_15(self):
        fees = poshmark_fees(m(platform="poshmark", price=40.00))
        assert fees["commission"] == pytest.approx(8.00)

    def test_commission_on_item_price_only(self):
        # shipping charged is buyer-paid via Poshmark prepaid label:
        # at price 40 the fee is 20% * 40 = 8, NOT 20% * (40 + shipping)
        fees = poshmark_fees(m(platform="poshmark", price=40.00, shipping_charged=7.0))
        assert fees["commission"] == pytest.approx(8.00)

    def test_net_profit_flat_tier(self):
        # price 10: fee 2.95; net = 10 + 5 - 2.95 - 8 - 4 = 0.05
        r = calculate(m(platform="poshmark", price=10.0))
        assert r.total_fees == pytest.approx(2.95)
        assert r.net_profit == pytest.approx(0.05, abs=0.01)

    def test_net_profit_pct_tier(self):
        # price 30: fee 6; net = 35 - 6 - 8 - 4 = 17
        r = calculate(m(platform="poshmark", price=30.0))
        assert r.total_fees == pytest.approx(6.00)
        assert r.net_profit == pytest.approx(17.00, abs=0.01)

    def test_breakeven_flat_tier(self):
        # price 10 -> flat regime: need = 8 + 4 + 2.95 = 14.95; revenue-based
        # pct = 0 -> price = 14.95 - 5 = 9.95 (< 15, consistent)
        assert breakeven_price(m(platform="poshmark", price=10.0)) == pytest.approx(9.95, abs=0.01)

    def test_breakeven_pct_tier(self):
        # price 30 -> pct regime: (P + 5)*1 - 0.20*P = 12 -> 0.8P = 7 -> P = 8.75
        # ...but 8.75 < 15 belongs to the flat tier; the solver must resolve:
        # flat tier root: 8 + 4 + 2.95 - 5 = 9.95 (< 15) -> wins
        assert breakeven_price(m(platform="poshmark", price=30.0)) == pytest.approx(9.95, abs=0.01)

    def test_breakeven_high_cost_uses_pct_tier(self):
        # cost 13: flat root = 13 + 4 + 2.95 - 5 = 14.95 < 15 -> still flat
        assert breakeven_price(m(platform="poshmark", price=30.0, product_cost=13.0)) \
            == pytest.approx(14.95, abs=0.01)

    def test_breakeven_above_tier_boundary(self):
        # cost 20: flat root = 20 + 4 + 2.95 - 5 = 21.95 >= 15 -> pct tier:
        # 0.8P = 20 + 4 - 5 -> P = 23.75
        be = breakeven_price(m(platform="poshmark", price=30.0, product_cost=20.0))
        assert be == pytest.approx(23.75, abs=0.01)
        r = calculate(m(platform="poshmark", price=be, product_cost=20.0))
        assert r.net_profit == pytest.approx(0.0, abs=0.02)

    def test_breakeven_zero_net_roundtrip_both_tiers(self):
        for cost in (3.0, 10.0, 25.0):
            be = breakeven_price(m(platform="poshmark", product_cost=cost))
            r = calculate(m(platform="poshmark", price=be, product_cost=cost))
            assert r.net_profit == pytest.approx(0.0, abs=0.03), cost

    def test_vat_applies(self):
        r = calculate(m(platform="poshmark", vat_percent=20))
        assert r.vat == pytest.approx(0.20 * 35)

    def test_flat_fee_converted_in_eur(self):
        raw = poshmark_fees(m(platform="poshmark", price=10.0, currency="EUR"))
        assert raw["commission"] == pytest.approx(round(2.95 / 1.08, 4))


class TestNewPlatformsInAggregate:
    def test_depop_cheaper_than_etsy_for_small_items(self):
        inp = dict(price=10.0, product_cost=3.0, shipping_paid=0.0, shipping_charged=0.0)
        r_depop = calculate(FeeInputs(platform="depop", **inp))
        r_posh = calculate(FeeInputs(platform="poshmark", **inp))
        # Depop: 10% = 1.00; Poshmark: flat 2.95
        assert r_depop.total_fees < r_posh.total_fees

    def test_depop_cheaper_than_poshmark_at_high_prices(self):
        # 20% commission beats 10% marketplace fee nowhere above the tier
        # boundary: at $100 Poshmark takes $20 vs Depop's $10
        inp = dict(price=100.0, product_cost=10.0, shipping_paid=0.0, shipping_charged=0.0)
        r_depop = calculate(FeeInputs(platform="depop", **inp))
        r_posh = calculate(FeeInputs(platform="poshmark", **inp))
        assert r_depop.total_fees < r_posh.total_fees

    def test_depop_cheaper_than_poshmark_at_low_prices_too(self):
        # under $15: Depop 10% of a $14 item ($1.40) vs Poshmark flat $2.95
        inp = dict(price=14.0, product_cost=5.0, shipping_paid=0.0, shipping_charged=0.0)
        r_depop = calculate(FeeInputs(platform="depop", **inp))
        r_posh = calculate(FeeInputs(platform="poshmark", **inp))
        assert r_depop.total_fees < r_posh.total_fees

    def test_poshmark_tier_boundary_discontinuity(self):
        # net just below $15 (flat) is LOWER than net at exactly $15 (pct kicks
        # in only above 2.95 -> 0.20*15 = 3.00 > 2.95): net drops by $0.05
        net_14_99 = calculate(m(platform="poshmark", price=14.99)).net_profit
        net_15 = calculate(m(platform="poshmark", price=15.00)).net_profit
        assert net_15 < net_14_99
