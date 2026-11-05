"""Multi-currency support: EUR-based ECB reference rates with offline fallback.

The SPA works fully offline, so rates come in two layers:

1. ``FALLBACK_RATES`` — hardcoded constants (documented approximations of the
   ECB reference rates as of late 2025). Always available, used by tests.
2. ``load_rates()`` — tries a cached JSON file (24h TTL), then fetches fresh
   rates from the free ECB feed (no API key). Failures degrade gracefully:
   stale cache -> hardcoded fallback.

Rates are EUR-based: 1 EUR = rate[code] units of ``code``. Fallback rates
last verified 2026-11-05.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
CACHE_TTL_HOURS = 24

# Offline fallback (approx. ECB reference rates; last verified 2026-11-05). EUR-based.
FALLBACK_RATES: dict[str, float] = {
    "EUR": 1.0,
    "USD": 1.08,
    "GBP": 0.855,
    "UAH": 45.20,
}

SYMBOLS: dict[str, str] = {
    "EUR": "\u20ac",
    "USD": "$",
    "GBP": "\u00a3",
    "UAH": "\u20b4",
}

SUPPORTED = tuple(sorted(FALLBACK_RATES))

_rates: dict[str, float] = dict(FALLBACK_RATES)


def normalize(code: str) -> str:
    """Upper-case a currency code; unsupported/empty codes fall back to USD."""
    c = (code or "USD").strip().upper()
    return c if c in FALLBACK_RATES else "USD"


def is_supported(code: str) -> bool:
    return (code or "").strip().upper() in FALLBACK_RATES


def set_rates(rates: dict[str, float]) -> None:
    """Update the live rate table (EUR-based). Unknown codes are ignored."""
    for k, v in rates.items():
        c = (k or "").strip().upper()
        if c in FALLBACK_RATES and isinstance(v, (int, float)) and v > 0:
            _rates[c] = float(v)


def reset_rates() -> None:
    """Restore the hardcoded fallback rates (used by tests)."""
    _rates.clear()
    _rates.update(FALLBACK_RATES)


def get_rates() -> dict[str, float]:
    return dict(_rates)


def rate(code: str) -> float:
    return _rates[normalize(code)]


def convert(amount: float, frm: str, to: str) -> float:
    """Convert between any two supported currencies (EUR-based rates)."""
    f, t = normalize(frm), normalize(to)
    return amount * rate(t) / rate(f)


def from_usd(amount_usd: float, currency: str) -> float:
    """Convert a USD-denominated amount (platform fixed fees) to ``currency``."""
    return convert(amount_usd, "USD", currency)


def format_money(amount: float, currency: str) -> str:
    sym = SYMBOLS[normalize(currency)]
    return f"-{sym}{abs(amount):,.2f}" if amount < 0 else f"{sym}{amount:,.2f}"


# ---------------------------------------------------------------------------
# ECB feed: parse + fetch + cache
# ---------------------------------------------------------------------------

def parse_ecb_xml(xml_text: str) -> dict[str, float]:
    """Parse the ECB eurofxref-daily.xml into an EUR-based rate table."""
    root = ET.fromstring(xml_text)
    rates: dict[str, float] = {"EUR": 1.0}
    for cube in root.iter():
        code = cube.get("currency")
        r = cube.get("rate")
        if code and r:
            try:
                rates[code.strip().upper()] = float(r)
            except ValueError:
                continue
    return rates


def fetch_ecb_rates(timeout: int = 10) -> dict[str, float]:
    """Fetch live ECB reference rates (free, no API key). Raises on failure."""
    with urlopen(ECB_URL, timeout=timeout) as resp:
        return parse_ecb_xml(resp.read().decode("utf-8", "replace"))


def load_rates(
    cache_path: Path | None,
    ttl_hours: int = CACHE_TTL_HOURS,
    now: datetime | None = None,
    fetch=fetch_ecb_rates,
    offline: bool = False,
) -> dict[str, float]:
    """Return a rate table: fresh cache -> live fetch -> stale cache -> fallback.

    A successful fetch is written to ``cache_path``. Network failures never
    raise — offline use is a first-class case.
    """
    now = now or datetime.now(timezone.utc)
    cached = _read_cache(cache_path)
    if not offline and cached and _cache_fresh(cached, now, ttl_hours):
        set_rates(cached["rates"])
        return get_rates()
    if not offline:
        try:
            live = fetch()
            set_rates(live)
            _write_cache(cache_path, live, now)
            return get_rates()
        except Exception:
            pass  # offline: fall through to stale cache / constants
    if cached:
        set_rates(cached["rates"])
    return get_rates()


def _read_cache(cache_path: Path | None) -> dict | None:
    if cache_path is None:
        return None
    try:
        data = json.loads(Path(cache_path).read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("rates"), dict) and data.get("ts"):
            return data
    except Exception:
        pass
    return None


def _cache_fresh(cached: dict, now: datetime, ttl_hours: int) -> bool:
    try:
        ts = cached["ts"]
        dt = datetime.fromtimestamp(ts, tz=timezone.utc) if isinstance(ts, (int, float)) \
            else datetime.fromisoformat(str(ts))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt).total_seconds() < ttl_hours * 3600
    except Exception:
        return False


def _write_cache(cache_path: Path | None, rates: dict[str, float], now: datetime) -> None:
    if cache_path is None:
        return
    try:
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cache_path).write_text(
            json.dumps({"ts": now.timestamp(), "rates": rates}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass  # cache write is best-effort
