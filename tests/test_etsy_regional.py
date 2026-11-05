"""Tests for Etsy regional payment processing variations (seller country)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.fees import (  # noqa: E402
    ETSY,
    ETSY_REGIONAL,
    FeeInputs,
    breakeven_price,
    calculate,
    etsy_fees,
    etsy_payment_terms,
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


class TestPaymentTerms:
    def test_table_covers_documented_countries(self):
        for cc in ("US", "GB", "DE", "FR", "IT", "ES", "CA", "AU"):
            assert cc in ETSY_REGIONAL

    def test_us_matches_default(self):
        pct, fixed = etsy_payment_terms("US")
        assert pct == pytest.approx(ETSY["payment_pct"])
        assert fixed == pytest.approx(ETSY["payment_fixed"])

    def test_unknown_country_falls_back_to_default(self):
        for cc in ("", "UA", "PL", "ZZ"):
            pct, fixed = etsy_payment_terms(cc)
            assert pct == pytest.approx(ETSY["payment_pct"])
            assert fixed == pytest.approx(ETSY["payment_fixed"])

    def test_case_and_whitespace_normalized(self):
        pct, _ = etsy_payment_terms(" gb ")
        assert pct == pytest.approx(ETSY_REGIONAL["GB"]["payment_pct"])


class TestEtsyFeesRegional:
    def test_uk_seller_pays_4pct(self):
        # base = 35; GB: 4% = 1.40 vs default 3% = 1.05
        fees = etsy_fees(m(country="GB"))
        assert fees["payment_processing"] == pytest.approx(0.04 * 35 + ETSY_REGIONAL["GB"]["payment_fixed_usd"], abs=0.01)

    def test_italy_seller_pays_4_5pct(self):
        fees = etsy_fees(m(country="IT"))
        assert fees["payment_processing"] == pytest.approx(0.045 * 35 + 0.33, abs=0.01)

    def test_uk_seller_also_gets_regulatory_fee(self):
        fees = etsy_fees(m(country="GB"))
        assert "regulatory" in fees

    def test_us_seller_no_regulatory_fee(self):
        fees = etsy_fees(m(country="US"))
        assert "regulatory" not in fees

    def test_de_seller_no_regulatory_fee(self):
        # DE is not in the regulatory-fee list (GB/FR/IT/ES)
        fees = etsy_fees(m(country="DE"))
        assert "regulatory" not in fees

    def test_regional_rate_flows_into_calculate(self):
        r_us = calculate(m(country="US"))
        r_gb = calculate(m(country="GB"))
        # GB pays +1% of 35 (= +0.35) minus the fixed delta (-0.01)
        assert r_gb.total_fees > r_us.total_fees
        assert r_gb.net_profit < r_us.net_profit

    def test_regional_fixed_fee_converted_to_working_currency(self):
        r = calculate(m(country="GB", currency="GBP"))
        # £0.20 fixed is stored as ~$0.24 USD-equivalent; in GBP working
        # currency it converts back to ~0.24 * 0.855/1.08 = 0.19
        assert r.fees["payment_processing"] == pytest.approx(
            0.04 * 35 + 0.24 * 0.855 / 1.08, abs=0.01)

    def test_breakeven_uses_regional_pct(self):
        be_us = breakeven_price(m(country="US"))
        be_gb = breakeven_price(m(country="GB"))
        # higher UK payment pct -> higher breakeven price
        assert be_gb > be_us
        r = calculate(m(country="GB", price=be_gb))
        assert r.net_profit == pytest.approx(0.0, abs=0.03)

    def test_vinted_style_empty_country_unchanged(self):
        # regression guard: no country -> exactly the old default math
        fees = etsy_fees(m(country=""))
        assert fees["payment_processing"] == pytest.approx(
            ETSY["payment_pct"] * 35 + ETSY["payment_fixed"], abs=0.001)
