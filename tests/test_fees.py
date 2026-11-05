"""Tests for fee calculations against real, documented platform fee structures."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.fees import (  # noqa: E402
    AMAZON_REFERRAL,
    ETSY,
    FeeInputs,
    amazon_fees,
    breakeven_price,
    calculate,
    etsy_fees,
    parse_csv,
    raise_price,
    shopify_fees,
)


def m(**kw):
    defaults = dict(platform="etsy", price=30.0, product_cost=8.0,
                    shipping_paid=4.0, shipping_charged=5.0)
    defaults.update(kw)
    return FeeInputs(**defaults)


# ---------------------------------------------------------------------------
# Etsy
# ---------------------------------------------------------------------------

class TestEtsy:
    def test_basic_fees(self):
        # price 30, shipping charged 5 -> fee base = 35
        fees = etsy_fees(m())
        assert fees["listing"] == pytest.approx(0.20)
        assert fees["transaction"] == pytest.approx(0.065 * 35)   # 2.275
        assert fees["payment_processing"] == pytest.approx(0.03 * 35 + 0.25)  # 1.30
        assert "offsite_ads" not in fees
        assert sum(fees.values()) == pytest.approx(0.20 + 2.275 + 1.30)

    def test_offsite_ads_15pct(self):
        fees = etsy_fees(m(offsite_ads=True))
        assert fees["offsite_ads"] == pytest.approx(0.15 * 35)  # 5.25

    def test_net_profit_matches_evidence_case(self):
        # Research case: seller nets $18-20 on a $30 item after all fees.
        r = calculate(m())
        assert r.revenue == pytest.approx(35.0)
        assert r.total_fees == pytest.approx(3.775, abs=0.01)
        # net = 35 - 3.775 fees - 8 cost - 4 shipping
        assert r.net_profit == pytest.approx(19.225, abs=0.01)
        assert r.margin_pct == pytest.approx(19.225 / 35.0 * 100, abs=0.01)

    def test_breakeven_zero_net(self):
        be = breakeven_price(m())
        r = calculate(m(price=be))
        assert r.net_profit == pytest.approx(0.0, abs=0.02)

    def test_breakeven_manual_value(self):
        # pct_total = 0.065 + 0.03 = 0.095; fixed = 0.20 + 0.25 = 0.45
        # need = 8 + 4 + 0.45 = 12.45 -> total = 12.45/0.905 = 13.7569...
        # price = total - 5 = 8.7569 -> 8.76
        assert breakeven_price(m()) == pytest.approx(8.76, abs=0.01)

    def test_breakeven_with_offsite_ads(self):
        # pct_total = 0.095 + 0.15 = 0.245; denom = 0.755
        # need = 12.45 -> total = 16.4901; price = 11.4901 -> 11.49
        inp = m(offsite_ads=True)
        assert breakeven_price(inp) == pytest.approx(11.49, abs=0.01)

    def test_vat_deducted(self):
        r = calculate(m(vat_percent=20.0))
        assert r.vat == pytest.approx(0.20 * 35)
        r0 = calculate(m())
        assert r0.net_profit - r.net_profit == pytest.approx(7.0)


# ---------------------------------------------------------------------------
# Shopify
# ---------------------------------------------------------------------------

class TestShopify:
    def test_basic_fees(self):
        fees = shopify_fees(m(platform="shopify"))
        assert fees["payment_processing"] == pytest.approx(0.029 * 35 + 0.30)  # 1.315
        assert "monthly_fee_share" not in fees

    def test_monthly_fee_spread(self):
        # $39/mo over 100 orders -> $0.39 per order
        fees = shopify_fees(m(platform="shopify", shopify_monthly_fee=39.0,
                              shopify_monthly_orders=100))
        assert fees["monthly_fee_share"] == pytest.approx(0.39)

    def test_monthly_fee_without_orders_ignored(self):
        fees = shopify_fees(m(platform="shopify", shopify_monthly_fee=39.0,
                              shopify_monthly_orders=0))
        assert "monthly_fee_share" not in fees

    def test_net(self):
        r = calculate(m(platform="shopify", shopify_monthly_fee=39.0,
                        shopify_monthly_orders=100))
        # fees = 1.315 + 0.39 = 1.705; net = 35 - 1.705 - 8 - 4 = 21.295
        assert r.net_profit == pytest.approx(21.295, abs=0.01)
        # pct=0.029; fixed = 0.30 + 0.39 = 0.69; need = 12.69/0.971 = 13.0711 -> price 8.07
        assert breakeven_price(m(platform="shopify", shopify_monthly_fee=39.0,
                                 shopify_monthly_orders=100)) == pytest.approx(8.07, abs=0.01)


# ---------------------------------------------------------------------------
# Amazon
# ---------------------------------------------------------------------------

class TestAmazon:
    def test_referral_by_category(self):
        assert amazon_fees(m(platform="amazon", amazon_category="electronics"))["referral"] \
            == pytest.approx(0.08 * 35)
        assert amazon_fees(m(platform="amazon", amazon_category="clothing"))["referral"] \
            == pytest.approx(0.17 * 35)
        # unknown category falls back to the 15% default
        assert amazon_fees(m(platform="amazon", amazon_category="quantum_gear"))["referral"] \
            == pytest.approx(0.15 * 35)

    def test_per_item_fee(self):
        fees = amazon_fees(m(platform="amazon", amazon_per_item_fee=True, units=2))
        assert fees["per_item"] == pytest.approx(1.98)

    def test_full_calc(self):
        r = calculate(m(platform="amazon", amazon_category="electronics"))
        assert r.total_fees == pytest.approx(2.80)
        assert r.net_profit == pytest.approx(35 - 2.80 - 8 - 4)
        # pct=0.08, fixed=0: need = 12/0.92 = 13.0435 total -> price = 8.04
        assert r.breakeven_price == pytest.approx(8.04, abs=0.01)


# ---------------------------------------------------------------------------
# Cross-platform comparison / edge cases
# ---------------------------------------------------------------------------

class TestComparisonAndEdges:
    def test_channel_comparison_etsy_vs_shopify(self):
        etsy = calculate(m())
        shop = calculate(m(platform="shopify"))
        # Etsy's 6.5% + 3% stack > Shopify's 2.9% at this order size
        assert etsy.total_fees > shop.total_fees
        assert shop.net_profit > etsy.net_profit

    def test_zero_price_margin_zero(self):
        r = calculate(m(price=0.0, shipping_charged=0.0))
        assert r.margin_pct == 0.0
        assert r.net_profit == pytest.approx(-12.45)

    def test_unknown_platform_raises(self):
        with pytest.raises(ValueError):
            calculate(m(platform="ebay"))

    def test_negative_inputs_clamped(self):
        r = calculate(m(price=-5, product_cost=-1, shipping_paid=-2, shipping_charged=-3))
        assert r.revenue == pytest.approx(0.0)

    def test_fee_stacking_note(self):
        # Fee stacking: same item sold at 30, margin must reflect ALL stacked fees,
        # not just the headline transaction rate.
        r = calculate(m())
        assert r.total_fees > 0.065 * 35  # more than the headline 6.5% alone


# ---------------------------------------------------------------------------
# What-if slider & CSV batch
# ---------------------------------------------------------------------------

class TestWhatIfAndCsv:
    def test_raise_price_increases_margin(self):
        base = calculate(m())
        raised = raise_price(m(), 5.0)
        assert raised.revenue == pytest.approx(40.0)  # 35 + 5
        assert raised.net_profit > base.net_profit
        assert raised.margin_pct > base.margin_pct

    def test_csv_roundtrip(self):
        csv = (
            "name,platform,price,product_cost,shipping_paid,shipping_charged,offsite_ads,vat_percent\n"
            "mug,etsy,30,8,4,5,true,20\n"
            "tshirt,shopify,25,10,3,0,false,0\n"
        )
        rows = parse_csv(csv)
        assert len(rows) == 2
        r1 = calculate(rows[0])
        assert r1.net_profit == pytest.approx(35 - (0.20 + 2.275 + 1.30 + 5.25) - 7.0 - 8 - 4,
                                              abs=0.01)
        r2 = calculate(rows[1])
        # revenue 25 (no shipping charged); fees 1.025; cost 10 + shipping 3
        assert r2.net_profit == pytest.approx(25 - (0.029 * 25 + 0.30) - 10 - 3, abs=0.01)

    def test_csv_missing_column_raises(self):
        with pytest.raises(ValueError, match="missing columns"):
            parse_csv("name,price\nx,10\n")

    def test_csv_empty(self):
        assert parse_csv("") == []


# ---------------------------------------------------------------------------
# Alpha: Etsy Ads fee (12.5%) + regulatory operating fee (0.32%)
# ---------------------------------------------------------------------------

class TestEtsyAdsAndRegulatory:
    def test_etsy_ads_fee_12_5pct(self):
        fees = etsy_fees(m(etsy_ads=True))
        assert fees["etsy_ads"] == pytest.approx(0.125 * 35)  # 4.375

    def test_etsy_ads_excluded_by_default(self):
        assert "etsy_ads" not in etsy_fees(m())

    def test_regulatory_fee_for_supported_countries(self):
        for c in ("GB", "UK", "FR", "IT", "ES"):
            fees = etsy_fees(m(country=c))
            assert fees["regulatory"] == pytest.approx(0.0032 * 35), c

    def test_regulatory_fee_absent_without_country(self):
        assert "regulatory" not in etsy_fees(m())
        assert "regulatory" not in etsy_fees(m(country="us"))
        assert "regulatory" not in etsy_fees(m(country="de"))

    def test_regulatory_country_is_case_insensitive(self):
        fees = etsy_fees(m(country="fr"))
        assert fees["regulatory"] == pytest.approx(0.0032 * 35)

    def test_full_stack_with_ads_and_regulatory(self):
        r = calculate(m(etsy_ads=True, country="GB"))
        # fees: 0.20 + 2.275 + 1.30 + 4.375 + 0.112 = 8.262
        assert r.total_fees == pytest.approx(0.20 + 2.275 + 1.30 + 4.375 + 0.112, abs=0.01)
        assert r.net_profit == pytest.approx(35 - 8.262 - 8 - 4, abs=0.01)

    def test_breakeven_with_ads_and_regulatory(self):
        # pct_total = 0.065 + 0.03 + 0.125 + 0.0032 = 0.2232; denom = 0.7768
        # need = 12.45 -> total = 16.0275; price = 11.0275 -> 11.03
        assert breakeven_price(m(etsy_ads=True, country="UK")) == pytest.approx(11.03, abs=0.01)

    def test_csv_new_columns(self):
        rows = parse_csv(
            "platform,price,product_cost,shipping_paid,shipping_charged,etsy_ads,country\n"
            "etsy,30,8,4,5,true,FR\n"
            "etsy,30,8,4,5,false,\n"
        )
        assert etsy_fees(rows[0])["regulatory"] == pytest.approx(0.112)
        assert etsy_fees(rows[0])["etsy_ads"] == pytest.approx(4.375)
        assert "regulatory" not in etsy_fees(rows[1])


# ---------------------------------------------------------------------------
# Alpha: generated JS constants must match the Python source of truth
# ---------------------------------------------------------------------------

class TestGeneratedJsSync:
    def test_generated_payload_matches_python(self):
        import generate_js
        payload = generate_js.PAYLOAD
        assert payload["ETSY"] == {
            "listing": ETSY["listing_fee"],
            "transaction": ETSY["transaction_pct"],
            "payPct": ETSY["payment_pct"],
            "payFixed": ETSY["payment_fixed"],
            "offsiteAds": ETSY["offsite_ads_pct"],
            "ads": ETSY["ads_pct"],
            "regulatory": ETSY["regulatory_pct"],
        }
        assert payload["AMAZON_REFERRAL"] == AMAZON_REFERRAL
        assert payload["AMAZON_PER_ITEM"] == 0.99
        assert payload["SHOPIFY"] == {"payPct": 0.029, "payFixed": 0.30}
        assert set(payload["REGULATORY_COUNTRIES"]) == {"GB", "UK", "FR", "IT", "ES"}

    def test_committed_generated_file_is_fresh(self):
        """The committed core/fees.generated.js must equal a fresh generation."""
        import generate_js
        committed = Path(generate_js.__file__).parent.joinpath(
            "core", "fees.generated.js").read_text(encoding="utf-8")
        assert committed == generate_js.build_js(), (
            "core/fees.generated.js is stale — run: python generate_js.py"
        )

    def test_generated_file_is_valid_js_object(self):
        import generate_js
        text = Path(generate_js.__file__).parent.joinpath(
            "core", "fees.generated.js").read_text(encoding="utf-8")
        payload = json.loads(text.split("window.ML_FEES = ", 1)[1].rstrip(";\n"))
        assert payload["ETSY"]["ads"] == ETSY["ads_pct"]
        assert payload["ETSY"]["regulatory"] == ETSY["regulatory_pct"]
