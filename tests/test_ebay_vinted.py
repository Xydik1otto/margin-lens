"""Tests for eBay and Vinted fee structures."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.fees import (  # noqa: E402
    EBAY,
    FeeInputs,
    breakeven_price,
    calculate,
    ebay_fees,
    vinted_fees,
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


class TestEbay:
    def test_final_value_fee(self):
        # base = 30 + 5 = 35 -> 13.25% = 4.6375
        fees = ebay_fees(m(platform="ebay"))
        assert fees["final_value"] == pytest.approx(0.1325 * 35)

    def test_per_order_fixed_fee(self):
        fees = ebay_fees(m(platform="ebay"))
        assert fees["per_order"] == pytest.approx(0.40)

    def test_per_order_fee_once_per_order(self):
        # $0.40 is per ORDER, not per unit — 3 units in one order still pay once
        fees = ebay_fees(m(platform="ebay", units=3))
        assert fees["per_order"] == pytest.approx(0.40)

    def test_constants(self):
        assert EBAY["final_value_pct"] == pytest.approx(0.1325)
        assert EBAY["per_order_fixed"] == pytest.approx(0.40)

    def test_net_profit(self):
        # net = 35 - (4.6375 + 0.40) - 8 - 4 = 17.9625
        r = calculate(m(platform="ebay"))
        assert r.total_fees == pytest.approx(5.0375, abs=0.01)
        assert r.net_profit == pytest.approx(17.9625, abs=0.01)
        assert r.margin_pct == pytest.approx(17.9625 / 35 * 100, abs=0.01)

    def test_breakeven(self):
        # pct = 0.1325; fixed = 0.40; need = 8 + 4 + 0.40 = 12.40
        # total = 12.40/0.8675 = 14.2939...; price = 14.2939 - 5 = 9.29
        assert breakeven_price(m(platform="ebay")) == pytest.approx(9.29, abs=0.01)

    def test_breakeven_zero_net_roundtrip(self):
        be = breakeven_price(m(platform="ebay"))
        r = calculate(m(platform="ebay", price=be))
        assert r.net_profit == pytest.approx(0.0, abs=0.02)

    def test_fixed_fee_converted_in_eur(self):
        r = calculate(m(platform="ebay", currency="EUR"))
        # $0.40 -> EUR: 0.40 * 1/1.08 = 0.3704
        from core.fees import ebay_fees as ef
        raw = ef(m(platform="ebay", currency="EUR"))
        assert raw["per_order"] == pytest.approx(round(0.40 / 1.08, 4))

    def test_vat_applies(self):
        r = calculate(m(platform="ebay", vat_percent=20))
        assert r.vat == pytest.approx(0.20 * 35)

    def test_unknown_platform_still_raises(self):
        with pytest.raises(ValueError):
            calculate(m(platform="mercari"))


class TestVinted:
    def test_no_seller_fees(self):
        assert vinted_fees(m(platform="vinted")) == {}

    def test_zero_total_fees(self):
        r = calculate(m(platform="vinted"))
        assert r.total_fees == 0.0
        # net = 35 - 0 - 8 - 4 = 23
        assert r.net_profit == pytest.approx(23.0)

    def test_breakeven(self):
        # pct = 0, fixed = 0 -> need = 8 + 4 = 12 -> price = 12 - 5 = 7
        assert breakeven_price(m(platform="vinted")) == pytest.approx(7.0)

    def test_beats_ebay_on_fees(self):
        inp = dict(price=30.0, product_cost=8.0, shipping_paid=4.0, shipping_charged=5.0)
        r_ebay = calculate(FeeInputs(platform="ebay", **inp))
        r_vinted = calculate(FeeInputs(platform="vinted", **inp))
        assert r_vinted.net_profit > r_ebay.net_profit

    def test_shipping_discount_modeled_as_shipping_paid(self):
        # seller covers shipping -> it bites into the margin, fees stay zero
        r = calculate(m(platform="vinted", shipping_paid=5.0, shipping_charged=0.0))
        assert r.total_fees == 0.0
        assert r.net_profit == pytest.approx(30.0 - 8.0 - 5.0)

    def test_ad_profit_generic_across_platforms(self):
        from core.fees import ad_profit
        base = dict(price=30.0, product_cost=8.0, shipping_paid=4.0, shipping_charged=5.0)
        a_vinted = ad_profit(FeeInputs(platform="vinted", **base), ad_spend=10, ad_orders=2)
        # contribution = 35 - 0 fees - 12 = 23; profit = 2*23 - 10 = 36
        assert a_vinted["profit"] == pytest.approx(36.0)
        a_ebay = ad_profit(FeeInputs(platform="ebay", **base), ad_spend=10, ad_orders=2)
        # contribution = 35*0.8675 - 0.40 - 12 = 17.9625; profit = 2*17.9625 - 10
        assert a_ebay["profit"] == pytest.approx(2 * 17.9625 - 10, abs=0.02)
