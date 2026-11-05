"""Multi-currency fee calculations: fixed USD fees converted to working currency."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import fx  # noqa: E402
from core.fees import FeeInputs, breakeven_price, calculate, parse_csv  # noqa: E402


@pytest.fixture(autouse=True)
def _fallback_rates():
    fx.reset_rates()
    yield
    fx.reset_rates()


def m(**kw):
    defaults = dict(platform="etsy", price=30.0, product_cost=8.0,
                    shipping_paid=4.0, shipping_charged=5.0)
    defaults.update(kw)
    return FeeInputs(**defaults)


class TestCurrencyDefaults:
    def test_usd_is_default_and_unchanged(self):
        # All pre-existing numeric tests rely on USD being a no-op.
        r = calculate(m())
        assert r.total_fees == pytest.approx(3.775, abs=0.01)

    def test_sanitized_normalizes_currency(self):
        assert m(currency=" eur ").sanitized().currency == "EUR"
        assert m(currency="chf").sanitized().currency == "USD"  # unsupported -> USD


class TestFixedFeeConversion:
    def test_etsy_fixed_fees_in_eur(self):
        # 1 EUR = 1.08 USD -> $0.20 listing = €0.1852, $0.25 payment = €0.2315
        fees = calculate(m(currency="EUR"))
        listing = round(0.20 / 1.08, 4)
        pay_fixed = round(0.25 / 1.08, 4)
        # fees dict is rounded to 2 in FeeResult; verify against python-level fees
        from core.fees import etsy_fees
        raw = etsy_fees(m(currency="EUR"))
        assert raw["listing"] == pytest.approx(listing)
        assert raw["payment_processing"] == pytest.approx(0.03 * 35 + pay_fixed)

    def test_percent_fees_currency_neutral(self):
        r_usd = calculate(m())
        r_eur = calculate(m(currency="EUR"))
        # percentages identical; fixed parts differ only by conversion
        assert r_usd.fees["transaction"] == r_eur.fees["transaction"]

    def test_net_profit_in_eur_higher_by_fixed_delta(self):
        # EUR fixed fees are cheaper than USD ones (EUR is stronger), so net in EUR is higher
        r_usd = calculate(m())
        r_eur = calculate(m(currency="EUR"))
        fixed_usd = 0.20 + 0.25
        fixed_eur = round(0.20 / 1.08, 4) + round(0.25 / 1.08, 4)
        assert r_usd.net_profit - r_eur.net_profit == pytest.approx(fixed_eur - fixed_usd, abs=0.02)

    def test_amazon_per_item_in_uah(self):
        from core.fees import amazon_fees
        raw = amazon_fees(m(platform="amazon", amazon_per_item_fee=True, currency="UAH"))
        # $0.99 USD -> UAH: 0.99 * rate(UAH)/rate(USD) = 0.99 * 45.20/1.08
        assert raw["per_item"] == pytest.approx(round(0.99 * 45.20 / 1.08, 4))

    def test_shopify_fixed_in_gbp(self):
        from core.fees import shopify_fees
        raw = shopify_fees(m(platform="shopify", currency="GBP"))
        assert raw["payment_processing"] == pytest.approx(0.029 * 35 + round(0.30 * 0.855 / 1.08, 4))

    def test_breakeven_uses_converted_fixed_fees(self):
        # pct_total = 0.095 (Etsy), fixed = (0.20+0.25)/1.08 converted
        fixed_eur = round(0.20 / 1.08, 4) + round(0.25 / 1.08, 4)
        need = 8 + 4 + fixed_eur
        expected = round(need / 0.905 - 5, 2)
        assert breakeven_price(m(currency="EUR")) == pytest.approx(expected, abs=0.01)

    def test_returns_listing_loss_converted(self):
        r = calculate(m(currency="EUR", return_rate_pct=50))
        r_usd = calculate(m(return_rate_pct=50))
        # fixed fees cost less in EUR, so adjusted net is higher in EUR
        assert r.net_profit_adjusted > r_usd.net_profit_adjusted

    def test_csv_currency_column(self):
        rows = parse_csv("name,platform,price,product_cost,shipping_paid,shipping_charged,currency\n"
                         "mug,etsy,30,8,4,5,EUR\n")
        assert rows[0].currency == "EUR"

    def test_csv_default_currency_usd(self):
        rows = parse_csv("name,platform,price,product_cost,shipping_paid,shipping_charged\n"
                         "mug,etsy,30,8,4,5\n")
        assert rows[0].currency == "USD"
