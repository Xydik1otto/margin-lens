"""Pure fee-calculation logic for Margin Lens.

This module is the tested source of truth for fee structures. The SPA
(index.html) mirrors the same numbers in JavaScript for offline use.
All amounts are in the seller's currency units (USD by default).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


# ---------------------------------------------------------------------------
# Platform fee structures (public, documented rates as of 2025)
# ---------------------------------------------------------------------------

ETSY = {
    "listing_fee": 0.20,          # per item listed/sold
    "transaction_pct": 0.065,     # of (price + shipping charged)
    "payment_pct": 0.03,          # payment processing
    "payment_fixed": 0.25,
    "offsite_ads_pct": 0.15,      # optional; 12% for sellers > $10k/yr
    "ads_pct": 0.125,             # Etsy Ads fee on ads-attributed orders (optional)
    "regulatory_pct": 0.0032,     # regulatory operating fee (UK/FR/IT/ES)
}

# Countries where Etsy charges the 0.32% regulatory operating fee.
REGULATORY_COUNTRIES = {"GB", "UK", "FR", "IT", "ES"}

# Typical Etsy shipping rates by region (small parcel, USD), 2025.
# Used as one-click presets: what the seller pays vs what the customer pays.
ETSY_SHIPPING_PRESETS = {
    "us_domestic":  {"label": "США (внутрішня)",  "paid": 4.00, "charged": 5.00},
    "us_intl":      {"label": "США → міжнародне", "paid": 12.00, "charged": 14.00},
    "uk_domestic":  {"label": "UK (внутрішня)",   "paid": 3.50, "charged": 4.50},
    "eu_domestic":  {"label": "EU (внутрішня)",   "paid": 4.50, "charged": 6.00},
    "ca_domestic":  {"label": "Канада",           "paid": 5.00, "charged": 6.50},
    "au_domestic":  {"label": "Австралія",        "paid": 5.50, "charged": 7.00},
}

SHOPIFY = {
    "payment_pct": 0.029,         # online card rate (Basic plan)
    "payment_fixed": 0.30,
}

# Amazon referral (commission) percentages by category.
AMAZON_REFERRAL = {
    "default": 0.15,
    "electronics": 0.08,
    "home_kitchen": 0.15,
    "clothing": 0.17,
    "books": 0.15,
    "toys_games": 0.15,
    "beauty": 0.08,
    "grocery": 0.18,
    "jewelry": 0.20,
    "furniture": 0.15,
}
AMAZON_PER_ITEM_FEE = 0.99  # individual (non-pro) selling plan


@dataclass
class FeeInputs:
    platform: str                 # "etsy" | "shopify" | "amazon"
    price: float                  # item sale price
    product_cost: float           # COGS per unit
    shipping_paid: float          # what YOU pay for shipping
    shipping_charged: float       # what the customer pays you for shipping
    offsite_ads: bool = False     # Etsy offsite ads applied
    vat_percent: float = 0.0      # VAT/PDV liability, % of revenue
    shopify_monthly_fee: float = 0.0   # subscription, spread over orders
    shopify_monthly_orders: float = 0  # orders/month used for spreading
    amazon_category: str = "default"
    amazon_per_item_fee: bool = False  # individual selling plan $0.99
    etsy_ads: bool = False        # Etsy Ads fee (12.5%) on ads-attributed sales
    country: str = ""             # seller country code (ISO), for regulatory fee
    # aggregated over one order; keep 1 for a single-unit sale
    units: int = 1

    def sanitized(self) -> "FeeInputs":
        """Clamp nonsensical inputs so calculations never raise on user data."""
        return replace(
            self,
            platform=self.platform.lower().strip(),
            price=max(0.0, self.price),
            product_cost=max(0.0, self.product_cost),
            shipping_paid=max(0.0, self.shipping_paid),
            shipping_charged=max(0.0, self.shipping_charged),
            vat_percent=max(0.0, self.vat_percent),
            country=self.country.strip().upper(),
            units=max(1, int(self.units or 1)),
        )


@dataclass
class FeeResult:
    revenue: float                 # price + shipping charged
    fees: dict                     # named fee components
    total_fees: float
    product_cost: float
    shipping_paid: float
    vat: float
    net_profit: float
    margin_pct: float              # net / revenue * 100
    breakeven_price: float | None  # item price that yields net == 0
    shipping_margin: float = 0.0   # shipping_charged - shipping_paid (customer-side delta)


def shipping_margin(inp: FeeInputs) -> float:
    """Shipping profit/loss: what the customer pays vs what the seller pays."""
    return round(inp.shipping_charged - inp.shipping_paid, 2)


# ---------------------------------------------------------------------------
# Platform-specific fee breakdowns
# ---------------------------------------------------------------------------

def etsy_fees(inp: FeeInputs) -> dict:
    country = inp.country.strip().upper()
    fees = {"listing": ETSY["listing_fee"] * inp.units}
    base = inp.price + inp.shipping_charged
    fees["transaction"] = round(ETSY["transaction_pct"] * base, 4)
    fees["payment_processing"] = round(ETSY["payment_pct"] * base + ETSY["payment_fixed"], 4)
    if inp.offsite_ads:
        fees["offsite_ads"] = round(ETSY["offsite_ads_pct"] * base, 4)
    if inp.etsy_ads:
        fees["etsy_ads"] = round(ETSY["ads_pct"] * base, 4)
    if country in REGULATORY_COUNTRIES:
        fees["regulatory"] = round(ETSY["regulatory_pct"] * base, 4)
    return fees


def shopify_fees(inp: FeeInputs) -> dict:
    base = inp.price + inp.shipping_charged
    fees = {
        "payment_processing": round(SHOPIFY["payment_pct"] * base + SHOPIFY["payment_fixed"], 4),
    }
    if inp.shopify_monthly_fee > 0 and inp.shopify_monthly_orders > 0:
        # unknown volume: do not silently charge the whole fee
        share = inp.shopify_monthly_fee / inp.shopify_monthly_orders
        fees["monthly_fee_share"] = round(share * inp.units, 4)
    return fees


def amazon_fees(inp: FeeInputs) -> dict:
    base = inp.price + inp.shipping_charged
    pct = AMAZON_REFERRAL.get(inp.amazon_category.lower(), AMAZON_REFERRAL["default"])
    fees = {"referral": round(pct * base, 4)}
    if inp.amazon_per_item_fee:
        fees["per_item"] = AMAZON_PER_ITEM_FEE * inp.units
    return fees


_PLATFORM_FEE_FN = {
    "etsy": etsy_fees,
    "shopify": shopify_fees,
    "amazon": amazon_fees,
}


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def _pct_total(inp: FeeInputs) -> float:
    """Sum of percentage fees applied to revenue (used by breakeven solver)."""
    p = inp.platform
    parts = []
    if p == "etsy":
        parts = [ETSY["transaction_pct"], ETSY["payment_pct"]]
        if inp.offsite_ads:
            parts.append(ETSY["offsite_ads_pct"])
        if inp.etsy_ads:
            parts.append(ETSY["ads_pct"])
        if inp.country.strip().upper() in REGULATORY_COUNTRIES:
            parts.append(ETSY["regulatory_pct"])
    elif p == "shopify":
        parts = [SHOPIFY["payment_pct"]]
    elif p == "amazon":
        parts = [AMAZON_REFERRAL.get(inp.amazon_category.lower(), AMAZON_REFERRAL["default"])]
    else:
        raise ValueError(f"unknown platform: {inp.platform!r}")
    if inp.vat_percent:
        parts.append(inp.vat_percent / 100.0)
    return sum(parts)


def _fixed_fees(inp: FeeInputs) -> float:
    """Fixed (per-order) fee components independent of price."""
    p = inp.platform
    if p == "etsy":
        fixed = ETSY["listing_fee"] * inp.units + ETSY["payment_fixed"]
    elif p == "shopify":
        fixed = SHOPIFY["payment_fixed"]
        if inp.shopify_monthly_fee > 0 and inp.shopify_monthly_orders > 0:
            fixed += inp.shopify_monthly_fee / inp.shopify_monthly_orders * inp.units
    elif p == "amazon":
        fixed = AMAZON_PER_ITEM_FEE * inp.units if inp.amazon_per_item_fee else 0.0
    else:
        raise ValueError(f"unknown platform: {inp.platform!r}")
    return fixed


def breakeven_price(inp: FeeInputs) -> float | None:
    """Item price P at which net profit is exactly zero.

    net(P) = P_total * (1 - pct_total) - fixed_fees - product_cost - shipping_paid,
    where P_total = P + shipping_charged.
    """
    denom = 1.0 - _pct_total(inp)
    if denom <= 1e-9:
        return None  # percentage fees >= 100%: no break-even exists
    need = inp.product_cost + inp.shipping_paid + _fixed_fees(inp)
    total = need / denom
    return round(max(0.0, total - inp.shipping_charged), 2)


def calculate(inp: FeeInputs) -> FeeResult:
    inp = inp.sanitized()
    if inp.platform not in _PLATFORM_FEE_FN:
        raise ValueError(f"unknown platform: {inp.platform!r}")

    revenue = inp.price + inp.shipping_charged
    fees = _PLATFORM_FEE_FN[inp.platform](inp)
    total_fees = sum(fees.values())
    vat = round(revenue * inp.vat_percent / 100.0, 4) if inp.vat_percent else 0.0

    net = revenue - total_fees - vat - inp.product_cost - inp.shipping_paid
    margin = (net / revenue * 100.0) if revenue > 0 else 0.0

    return FeeResult(
        revenue=round(revenue, 2),
        fees={k: round(v, 2) for k, v in fees.items()},
        total_fees=round(total_fees, 2),
        product_cost=inp.product_cost,
        shipping_paid=inp.shipping_paid,
        vat=round(vat, 2),
        net_profit=round(net, 2),
        margin_pct=round(margin, 2),
        breakeven_price=breakeven_price(inp),
        shipping_margin=shipping_margin(inp),
    )


def raise_price(inp: FeeInputs, delta: float) -> FeeResult:
    """'What if I raise price by X' — recompute with price += delta."""
    return calculate(replace(inp, price=inp.price + delta))


def parse_csv(text: str) -> list[FeeInputs]:
    """Parse pasted CSV rows into FeeInputs.

    Expected header (order-insensitive, case-insensitive):
    name,platform,price,product_cost,shipping_paid,shipping_charged
    Optional columns: offsite_ads(true/false), vat_percent, units,
    shopify_monthly_fee, shopify_monthly_orders, amazon_category,
    amazon_per_item_fee(true/false).
    Returns a list of FeeInputs; 'name' is informational only.
    """
    rows: list[FeeInputs] = []
    lines = [ln for ln in (t.strip() for t in text.splitlines()) if ln]
    if not lines:
        return rows
    header = [h.strip().lower() for h in lines[0].split(",")]
    idx = {h: i for i, h in enumerate(header)}
    required = ("platform", "price", "product_cost", "shipping_paid", "shipping_charged")
    missing = [c for c in required if c not in idx]
    if missing:
        raise ValueError(f"CSV missing columns: {', '.join(missing)}")

    def col(row: list[str], name: str, default=""):
        i = idx.get(name)
        return row[i].strip() if i is not None and i < len(row) and row[i].strip() != "" else default

    def flag(row: list[str], name: str) -> bool:
        return col(row, name).lower() in ("1", "true", "yes", "y", "так", "on")

    for line in lines[1:]:
        row = [c.strip() for c in line.split(",")]
        rows.append(FeeInputs(
            platform=col(row, "platform", "etsy"),
            price=float(col(row, "price", "0")),
            product_cost=float(col(row, "product_cost", "0")),
            shipping_paid=float(col(row, "shipping_paid", "0")),
            shipping_charged=float(col(row, "shipping_charged", "0")),
            offsite_ads=flag(row, "offsite_ads"),
            etsy_ads=flag(row, "etsy_ads"),
            country=col(row, "country", ""),
            vat_percent=float(col(row, "vat_percent", "0")),
            shopify_monthly_fee=float(col(row, "shopify_monthly_fee", "0")),
            shopify_monthly_orders=float(col(row, "shopify_monthly_orders", "0")),
            amazon_category=col(row, "amazon_category", "default"),
            amazon_per_item_fee=flag(row, "amazon_per_item_fee"),
            units=int(col(row, "units", "1") or 1),
        ))
    return rows
