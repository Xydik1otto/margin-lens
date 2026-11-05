"""Tests for multi-currency support: ECB rates, offline fallback, conversion."""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import fx  # noqa: E402
from core.fx import (  # noqa: E402
    FALLBACK_RATES,
    SYMBOLS,
    convert,
    fetch_ecb_rates,
    format_money,
    from_usd,
    is_supported,
    load_rates,
    normalize,
    parse_ecb_xml,
    reset_rates,
    set_rates,
)


@pytest.fixture(autouse=True)
def _fallback_rates():
    """Every test runs against the hardcoded fallback rate table."""
    reset_rates()
    yield
    reset_rates()


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <Cube>
    <Cube time="2025-11-03">
      <Cube currency="USD" rate="1.0876"/>
      <Cube currency="GBP" rate="0.8408"/>
      <Cube currency="UAH" rate="45.1000"/>
      <Cube currency="PLN" rate="4.25"/>
    </Cube>
  </Cube>
</gesmes:Envelope>"""


class TestNormalize:
    def test_uppercase_and_strip(self):
        assert normalize(" eur ") == "EUR"
        assert normalize("uah") == "UAH"

    def test_unsupported_falls_back_to_usd(self):
        assert normalize("CHF") == "USD"
        assert normalize("") == "USD"
        assert normalize(None) == "USD"

    def test_is_supported(self):
        assert is_supported("uah") is True
        assert is_supported("CHF") is False


class TestConversion:
    def test_identity(self):
        assert convert(100, "USD", "USD") == 100.0
        assert convert(100, "EUR", "EUR") == 100.0

    def test_usd_to_eur_fallback(self):
        # 1 EUR = 1.08 USD -> 108 USD = 100 EUR
        assert convert(108, "USD", "EUR") == pytest.approx(100.0, abs=1e-9)

    def test_eur_to_uah(self):
        assert convert(2, "EUR", "UAH") == pytest.approx(90.4)

    def test_usd_to_gbp(self):
        assert convert(10, "USD", "GBP") == pytest.approx(10 * 0.855 / 1.08)

    def test_from_usd_matches_convert(self):
        assert from_usd(5, "EUR") == convert(5, "USD", "EUR")
        assert from_usd(5, "USD") == 5.0

    def test_set_rates_overrides(self):
        set_rates({"USD": 1.10})
        assert convert(110, "USD", "EUR") == pytest.approx(100.0)

    def test_set_rates_ignores_garbage(self):
        set_rates({"USD": -5, "XXX": 2, "GBP": "nope"})
        assert convert(10, "USD", "GBP") == pytest.approx(10 * 0.855 / 1.08)


class TestFormatMoney:
    def test_symbols(self):
        assert format_money(1.5, "USD") == "$1.50"
        assert format_money(1.5, "EUR") == "\u20ac1.50"
        assert format_money(1.5, "GBP") == "\u00a31.50"
        assert format_money(1.5, "UAH") == "\u20b41.50"

    def test_negative_and_thousands(self):
        assert format_money(-1234.5, "UAH") == "-\u20b41,234.50"
        assert format_money(0, "USD") == "$0.00"


class TestEcbParsing:
    def test_parse_sample_xml(self):
        rates = parse_ecb_xml(SAMPLE_XML)
        assert rates["EUR"] == 1.0
        assert rates["USD"] == pytest.approx(1.0876)
        assert rates["GBP"] == pytest.approx(0.8408)
        assert rates["UAH"] == pytest.approx(45.10)
        assert rates["PLN"] == pytest.approx(4.25)

    def test_parse_ignores_malformed_rate(self):
        rates = parse_ecb_xml('<Cube><Cube currency="USD" rate="abc"/></Cube>')
        assert "USD" not in rates

    def test_real_fetch_structure(self):
        """Live network probe is optional: skip if offline/blocked."""
        try:
            rates = fetch_ecb_rates(timeout=10)
        except Exception as e:  # network unavailable in sandbox
            pytest.skip(f"ECB unreachable: {e}")
        assert rates["EUR"] == 1.0
        assert rates["USD"] > 0.5


class TestLoadRates:
    def test_offline_uses_fallback_without_fetch(self):
        called = []

        def boom(*a, **kw):
            called.append(1)
            raise AssertionError("must not fetch in offline mode")

        rates = load_rates(None, offline=True, fetch=boom)
        assert rates == FALLBACK_RATES
        assert not called

    def test_fresh_cache_used_without_fetch(self, tmp_path):
        cache = tmp_path / "fx.json"
        cache.write_text('{"ts": %d, "rates": {"EUR": 1.0, "USD": 1.20}}'
                         % datetime.now(timezone.utc).timestamp(), encoding="utf-8")
        called = []

        def boom(*a, **kw):
            called.append(1)
            raise AssertionError("must not fetch when cache is fresh")

        rates = load_rates(cache, fetch=boom)
        assert rates["USD"] == 1.20
        assert not called

    def test_stale_cache_then_fetch_success_writes_new_cache(self, tmp_path):
        cache = tmp_path / "fx.json"
        old = datetime.now(timezone.utc).timestamp() - 48 * 3600
        cache.write_text(f'{{"ts": {old}, "rates": {{"USD": 1.20}}}}', encoding="utf-8")

        def fake_fetch():
            return {"EUR": 1.0, "USD": 1.05, "GBP": 0.80}

        rates = load_rates(cache, fetch=fake_fetch)
        assert rates["USD"] == 1.05
        assert rates["GBP"] == 0.80
        # cache rewritten with fresh data
        import json
        data = json.loads(cache.read_text(encoding="utf-8"))
        assert data["rates"]["USD"] == 1.05

    def test_fetch_failure_falls_back_to_stale_cache(self, tmp_path):
        cache = tmp_path / "fx.json"
        old = datetime.now(timezone.utc).timestamp() - 48 * 3600
        cache.write_text(f'{{"ts": {old}, "rates": {{"USD": 1.20}}}}', encoding="utf-8")

        def boom():
            raise OSError("offline")

        rates = load_rates(cache, fetch=boom)
        assert rates["USD"] == 1.20  # stale cache wins over constants

    def test_fetch_failure_no_cache_falls_back_to_constants(self, tmp_path):
        def boom():
            raise OSError("offline")

        rates = load_rates(tmp_path / "missing.json", fetch=boom)
        assert rates == FALLBACK_RATES

    def test_corrupt_cache_is_ignored(self, tmp_path):
        cache = tmp_path / "fx.json"
        cache.write_text("not json at all", encoding="utf-8")
        rates = load_rates(cache, offline=True)
        assert rates == FALLBACK_RATES


class TestSymbols:
    def test_all_supported_have_symbols(self):
        for code in FALLBACK_RATES:
            assert code in SYMBOLS and SYMBOLS[code]
