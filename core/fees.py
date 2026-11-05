"""Pure fee-calculation logic for Margin Lens.

This module is the tested source of truth for fee structures. The SPA
(index.html) mirrors the same numbers in JavaScript for offline use.

Currency: calculations are performed in the seller's working currency
(``FeeInputs.currency``, default USD). Percentage fees are currency-neutral;
fixed fees charged by platforms in USD (Etsy listing/payment fixed fee,
Amazon per-item fee, eBay per-order fee) are converted to the working
currency with ECB-based rates from ``core.fx`` (offline fallback constants).
Inputs the user types in their own currency (price, costs, Shopify monthly
subscription) are taken as-is.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from core.fx import from_usd, normalize


# ---------------------------------------------------------------------------
# Platform fee structures (public, documented rates; last verified 2026-11-05)
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

# Etsy payment processing varies by the seller's country of residence
# (domestic rate; last verified 2026-11-05). The fixed part is quoted in the
# seller's local currency; we store USD approximations and convert with
# fixed_in_currency().
# A seller outside this table pays the default rate (ETSY["payment_pct"] /
# ETSY["payment_fixed"] = 3% + $0.25, the US rate).
ETSY_REGIONAL = {
    "US": {"payment_pct": 0.03,  "payment_fixed_usd": 0.25},
    "GB": {"payment_pct": 0.04,  "payment_fixed_usd": 0.24},  # £0.20
    "DE": {"payment_pct": 0.04,  "payment_fixed_usd": 0.33},  # €0.30
    "FR": {"payment_pct": 0.04,  "payment_fixed_usd": 0.33},  # €0.30
    "IT": {"payment_pct": 0.045, "payment_fixed_usd": 0.33},  # €0.30
    "ES": {"payment_pct": 0.045, "payment_fixed_usd": 0.33},  # €0.30
    "CA": {"payment_pct": 0.03,  "payment_fixed_usd": 0.18},  # CA$0.25
    "AU": {"payment_pct": 0.04,  "payment_fixed_usd": 0.20},  # AU$0.30
}


def etsy_payment_terms(country: str) -> tuple[float, float]:
    """(payment_pct, payment_fixed_usd) for the seller's country.

    Unknown/empty country codes fall back to the US default rate. "UK" is
    accepted as an alias for "GB" (both spellings appear in Etsy docs).
    """
    c = (country or "").strip().upper()
    if c == "UK":
        c = "GB"
    if c in ETSY_REGIONAL:
        r = ETSY_REGIONAL[c]
        return r["payment_pct"], r["payment_fixed_usd"]
    return ETSY["payment_pct"], ETSY["payment_fixed"]


# Typical Etsy shipping rates by region (small parcel, USD; verified 2026-11-05).
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

# eBay: final value fee (~13.25% for most categories on the standard tier)
# plus a fixed $0.40 per-order fee. Category-specific rates exist (lower for
# some categories, higher add-ons for international buyers) — the standard
# tier below covers the typical case.
EBAY = {
    "final_value_pct": 0.1325,
    "per_order_fixed": 0.40,     # per order, regardless of item count
}

# Vinted: no seller fees at all. The buyer protection fee (+ shipping) is
# paid by the buyer, so the seller's fee stack is empty. If a seller offers
# a shipping discount, it is modeled via shipping_paid > 0.
VINTED = {"seller_pct": 0.0}

# Depop: flat 10% marketplace fee on the total sale (item + shipping charged).
# Payment processing (Depop Payments, ~3.3% + $0.45 in the US) is not part of
# the preset — sellers who want it can fold it into product_cost/shipping_paid.
DEPOP = {"marketplace_pct": 0.10}

# Poshmark: US-style two-tier commission on the item price (shipping is paid
# by the buyer through Poshmark's prepaid label, so it never touches the
# seller's fee stack):
#   - item price <  $15 -> flat $2.95
#   - item price >= $15 -> 20% of the item price
POSHMARK_FLAT_UNDER = 15.00
POSHMARK = {"flat_fee_under": 2.95, "pct_over": 0.20}


@dataclass
class FeeInputs:
    platform: str                 # "etsy"|"shopify"|"amazon"|"ebay"|"vinted"|"depop"|"poshmark"
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
    return_rate_pct: float = 0.0  # expected % of orders returned/refunded
    currency: str = "USD"         # working currency: EUR | USD | GBP | UAH
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
            currency=normalize(self.currency),
            return_rate_pct=min(max(0.0, self.return_rate_pct), 100.0),
            units=max(1, int(self.units or 1)),
        )


def fixed_in_currency(usd_amount: float, currency: str) -> float:
    """Platform fixed fee quoted in USD -> seller's working currency."""
    cur = normalize(currency)
    return from_usd(usd_amount, cur) if cur != "USD" else usd_amount


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
    net_profit_adjusted: float = 0.0    # net after the expected return rate
    margin_pct_adjusted: float = 0.0    # margin after the expected return rate


def shipping_margin(inp: FeeInputs) -> float:
    """Shipping profit/loss: what the customer pays vs what the seller pays."""
    return round(inp.shipping_charged - inp.shipping_paid, 2)


# ---------------------------------------------------------------------------
# Platform-specific fee breakdowns
# ---------------------------------------------------------------------------

def etsy_fees(inp: FeeInputs) -> dict:
    country = inp.country.strip().upper()
    pay_pct, pay_fixed_usd = etsy_payment_terms(country)
    fees = {"listing": round(fixed_in_currency(ETSY["listing_fee"], inp.currency) * inp.units, 4)}
    base = inp.price + inp.shipping_charged
    fees["transaction"] = round(ETSY["transaction_pct"] * base, 4)
    fees["payment_processing"] = round(
        pay_pct * base + fixed_in_currency(pay_fixed_usd, inp.currency), 4)
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
        "payment_processing": round(
            SHOPIFY["payment_pct"] * base
            + fixed_in_currency(SHOPIFY["payment_fixed"], inp.currency), 4),
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
        fees["per_item"] = round(
            fixed_in_currency(AMAZON_PER_ITEM_FEE, inp.currency) * inp.units, 4)
    return fees


def ebay_fees(inp: FeeInputs) -> dict:
    base = inp.price + inp.shipping_charged
    fees = {"final_value": round(EBAY["final_value_pct"] * base, 4)}
    fees["per_order"] = round(fixed_in_currency(EBAY["per_order_fixed"], inp.currency), 4)
    return fees


def vinted_fees(inp: FeeInputs) -> dict:
    return {}  # 0% seller fee; buyer protection is paid by the buyer


def depop_fees(inp: FeeInputs) -> dict:
    """Depop: flat 10% of the total sale (item + shipping charged)."""
    base = inp.price + inp.shipping_charged
    return {"marketplace": round(DEPOP["marketplace_pct"] * base, 4)}


def poshmark_fees(inp: FeeInputs) -> dict:
    """Poshmark: flat $2.95 under $15 item price, 20% of item price at $15+."""
    if inp.price < POSHMARK_FLAT_UNDER:
        fee = fixed_in_currency(POSHMARK["flat_fee_under"], inp.currency)
    else:
        fee = POSHMARK["pct_over"] * inp.price
    return {"commission": round(fee, 4)}


_PLATFORM_FEE_FN = {
    "etsy": etsy_fees,
    "shopify": shopify_fees,
    "amazon": amazon_fees,
    "ebay": ebay_fees,
    "vinted": vinted_fees,
    "depop": depop_fees,
    "poshmark": poshmark_fees,
}


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def _platform_pct_list(inp: FeeInputs) -> list[float]:
    """Percentage fee components for the platform (without VAT)."""
    p = inp.platform
    if p == "etsy":
        pay_pct, _ = etsy_payment_terms(inp.country)
        parts = [ETSY["transaction_pct"], pay_pct]
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
    elif p == "ebay":
        parts = [EBAY["final_value_pct"]]
    elif p == "vinted":
        parts = []
    elif p == "depop":
        parts = [DEPOP["marketplace_pct"]]
    elif p == "poshmark":
        # commission applies to the item price only; modeled against the
        # current price so the breakeven solver picks the right tier
        parts = [] if inp.price < POSHMARK_FLAT_UNDER else [POSHMARK["pct_over"]]
    else:
        raise ValueError(f"unknown platform: {inp.platform!r}")
    return parts


def _pct_total(inp: FeeInputs) -> float:
    """Sum of percentage fees applied to revenue (used by breakeven solver)."""
    parts = _platform_pct_list(inp)
    if inp.vat_percent:
        parts.append(inp.vat_percent / 100.0)
    return sum(parts)


def _fixed_fees(inp: FeeInputs) -> float:
    """Fixed (per-order) fee components independent of price."""
    p = inp.platform
    if p == "etsy":
        _, pay_fixed_usd = etsy_payment_terms(inp.country)
        fixed = fixed_in_currency(ETSY["listing_fee"], inp.currency) * inp.units \
            + fixed_in_currency(pay_fixed_usd, inp.currency)
    elif p == "shopify":
        fixed = fixed_in_currency(SHOPIFY["payment_fixed"], inp.currency)
        if inp.shopify_monthly_fee > 0 and inp.shopify_monthly_orders > 0:
            fixed += inp.shopify_monthly_fee / inp.shopify_monthly_orders * inp.units
    elif p == "amazon":
        fixed = round(fixed_in_currency(AMAZON_PER_ITEM_FEE, inp.currency) * inp.units, 4) \
            if inp.amazon_per_item_fee else 0.0
    elif p == "ebay":
        fixed = round(fixed_in_currency(EBAY["per_order_fixed"], inp.currency), 4)
    elif p == "vinted":
        fixed = 0.0
    elif p == "depop":
        fixed = 0.0
    elif p == "poshmark":
        fixed = round(fixed_in_currency(POSHMARK["flat_fee_under"], inp.currency), 4) \
            if inp.price < POSHMARK_FLAT_UNDER else 0.0
    else:
        raise ValueError(f"unknown platform: {inp.platform!r}")
    return fixed


def _poshmark_breakeven(inp: FeeInputs) -> float:
    """Poshmark breakeven across the two commission tiers (flat $2.95 under
    $15 item price, 20% of the item price at $15+). Shipping is buyer-paid
    (Poshmark prepaid label), so the commission never covers shipping charged.
    """
    vat = inp.vat_percent / 100.0
    flat = fixed_in_currency(POSHMARK["flat_fee_under"], inp.currency)
    cost = inp.product_cost + inp.shipping_paid
    # flat tier: (P + sc) * (1 - vat) - flat - cost = 0
    p_flat = ((cost + flat) / (1.0 - vat) - inp.shipping_charged
              if vat < 1.0 else float("inf"))
    # pct tier: (P + sc) * (1 - vat) - pct * P - cost = 0
    denom = 1.0 - vat - POSHMARK["pct_over"]
    p_pct = ((cost - inp.shipping_charged * (1.0 - vat)) / denom
             if denom > 1e-9 else float("inf"))
    if p_flat < POSHMARK_FLAT_UNDER:
        return round(max(0.0, p_flat), 2)
    return round(max(0.0, p_pct), 2)


def breakeven_price(inp: FeeInputs) -> float | None:
    """Item price P at which net profit is exactly zero.

    net(P) = P_total * (1 - pct_total) - fixed_fees - product_cost - shipping_paid,
    where P_total = P + shipping_charged.

    Poshmark is solved analytically across both commission tiers: the fee
    structure is discontinuous at $15 (flat $2.95 below, 20% of the item price
    at $15+), so a single linear solve would return a price that belongs to
    the wrong tier.
    """
    if inp.platform == "poshmark":
        return _poshmark_breakeven(inp)
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

    # Returns/refunds simulation: a returned sale refunds the customer in full,
    # platform percent fees are refunded, but the seller loses COGS, outgoing
    # shipping and (on Etsy) the non-refundable listing fee.
    net_adj, margin_adj = net, margin
    if inp.return_rate_pct > 0:
        rate = inp.return_rate_pct / 100.0
        listing_lost = fixed_in_currency(ETSY["listing_fee"], inp.currency) * inp.units \
            if inp.platform == "etsy" else 0.0
        net_returned = -(inp.product_cost + inp.shipping_paid + listing_lost)
        net_adj = (1.0 - rate) * net + rate * net_returned
        margin_adj = (net_adj / revenue * 100.0) if revenue > 0 else 0.0

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
        net_profit_adjusted=round(net_adj, 2),
        margin_pct_adjusted=round(margin_adj, 2),
    )


def ad_profit(inp: FeeInputs, ad_spend: float, ad_orders: float) -> dict:
    """Etsy Ads P&L: is the ad spend profitable at this ROAS?

    Contribution per order = revenue - percent fees (transaction + payment +
    regulatory, when applicable) - VAT - fixed fees - COGS - outgoing shipping.
    The ad cost is modeled explicitly via `ad_spend`, so the 12.5% Etsy Ads
    fee is NOT double-counted here.

    breakeven_roas = revenue_per_order / contribution_per_order — the ROAS at
    which the campaign stops losing money.
    """
    inp = inp.sanitized()
    ad_spend = max(0.0, ad_spend)
    ad_orders = max(0.0, ad_orders)
    revenue = inp.price + inp.shipping_charged
    pct_total = sum(_platform_pct_list(inp))
    fixed = _fixed_fees(inp)
    contribution = revenue * (1 - pct_total) - fixed - revenue * inp.vat_percent / 100.0 \
        - inp.product_cost - inp.shipping_paid
    total_revenue = ad_orders * revenue
    profit = ad_orders * contribution - ad_spend
    roas = (total_revenue / ad_spend) if ad_spend > 0 else None
    breakeven_roas = (revenue / contribution) if contribution > 1e-9 else None
    breakeven_spend = ad_orders * contribution
    return {
        "revenue_per_order": round(revenue, 2),
        "contribution_per_order": round(contribution, 4),
        "total_revenue": round(total_revenue, 2),
        "roas": round(roas, 2) if roas is not None else None,
        "breakeven_roas": round(breakeven_roas, 2) if breakeven_roas is not None else None,
        "breakeven_spend": round(breakeven_spend, 2),
        "profit": round(profit, 2),
    }


def raise_price(inp: FeeInputs, delta: float) -> FeeResult:
    """'What if I raise price by X' — recompute with price += delta."""
    return calculate(replace(inp, price=inp.price + delta))


def parse_csv(text: str) -> list[FeeInputs]:
    """Parse pasted CSV rows into FeeInputs.

    Expected header (order-insensitive, case-insensitive):
    name,platform,price,product_cost,shipping_paid,shipping_charged
    Optional columns: offsite_ads(true/false), vat_percent, units, currency,
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
            return_rate_pct=float(col(row, "return_rate_pct", "0")),
            shopify_monthly_fee=float(col(row, "shopify_monthly_fee", "0")),
            shopify_monthly_orders=float(col(row, "shopify_monthly_orders", "0")),
            amazon_category=col(row, "amazon_category", "default"),
            amazon_per_item_fee=flag(row, "amazon_per_item_fee"),
            currency=col(row, "currency", "USD"),
            units=int(col(row, "units", "1") or 1),
        ))
    return rows
