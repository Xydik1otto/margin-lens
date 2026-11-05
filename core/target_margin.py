"""Порівняння з цільовою маржею: розрив у п.п. і ціна для досягнення цілі.

UI: поле «Цільова маржа (%)» у картці результату калькулятора (index.html
містить JS-дзеркало gapToTarget / priceForTargetMargin — синхронізуйте обидва).

Визначення: маржа = net / revenue * 100 (net уже після VAT), як у
``core.fees.calculate``. Цільова ціна P розв'язується аналітично:

    (P + shipping_charged) * (1 - pct_total - target) =
        product_cost + shipping_paid + fixed_fees

де pct_total включає VAT (``_pct_total``). Якщо 1 - pct_total - target <= 0 —
ціль недосяжна жодною ціною (None). Для Poshmark (двохрівнева комісія зі
стрибком на $15) рівняння розв'язується по кожному рівню, береться
узгоджений — той самий підхід, що в ``fees._poshmark_breakeven``.
"""

from __future__ import annotations

from core.fees import (
    POSHMARK,
    POSHMARK_FLAT_UNDER,
    FeeInputs,
    _fixed_fees,
    _pct_total,
    calculate,
    fixed_in_currency,
)


def gap_to_target(margin_pct: float, target_pct: float | None,
                  eps: float = 0.05) -> dict:
    """Розрив між фактичною та цільовою маржею.

    Returns::

        {
            "actual":  фактична маржа, %,
            "target":  цільова маржа, % (None, якщо ціль не задана),
            "gap_pp":  фактична - цільова, у відсоткових пунктах,
            "status":  "above" | "on" | "below" | "none",
        }

    ``target_pct`` <= 0 або None означає «ціль не задана» -> status "none".
    Розриви в межах ``eps`` п.п. вважаються "on" (на цілі).
    """
    actual = round(margin_pct, 2)
    if target_pct is None or target_pct <= 0:
        return {"actual": actual, "target": None, "gap_pp": None,
                "status": "none"}
    gap = round(actual - target_pct, 2)
    if gap > eps:
        status = "above"
    elif gap >= -eps:
        status = "on"
    else:
        status = "below"
    return {"actual": actual, "target": target_pct, "gap_pp": gap,
            "status": status}


def price_for_target_margin(inp: FeeInputs, target_pct: float) -> float | None:
    """Ціна товару, при якій маржа дорівнює ``target_pct``.

    None — ціль недосяжна (відсоткові збори + VAT + ціль >= 100% виручки)
    або ціль не задана (<= 0). Повернення (return_rate_pct) не враховуються —
    як і в breakeven-ціні.
    """
    inp = inp.sanitized()
    t = target_pct / 100.0
    if t <= 0 or t >= 1.0:
        return None
    vat = inp.vat_percent / 100.0
    if inp.platform == "poshmark":
        return _poshmark_target_price(inp, t, vat)
    denom = 1.0 - _pct_total(inp) - t
    if denom <= 1e-9:
        return None
    need = inp.product_cost + inp.shipping_paid + _fixed_fees(inp)
    return round(max(0.0, need / denom - inp.shipping_charged), 2)


def _poshmark_target_price(inp: FeeInputs, t: float, vat: float) -> float | None:
    """Цільова ціна для Poshmark по обох тарифних рівнях (flat <$15 / 20% $15+).

    tier flat:   P * (1 - vat - t) = flat + cost + sp - sc * (1 - vat - t)
    tier pct:    P * (1 - vat - pct - t) = cost + sp - sc * (1 - vat - t)
    Береться рівень, узгоджений із розв'язком (як у _poshmark_breakeven).
    """
    sc = inp.shipping_charged
    base_cost = inp.product_cost + inp.shipping_paid
    flat = fixed_in_currency(POSHMARK["flat_fee_under"], inp.currency)
    d1 = 1.0 - vat - t
    p_flat = ((base_cost + flat - sc * d1) / d1) if d1 > 1e-9 else float("inf")
    if p_flat < POSHMARK_FLAT_UNDER:
        return round(max(0.0, p_flat), 2)
    d2 = 1.0 - vat - POSHMARK["pct_over"] - t
    if d2 <= 1e-9:
        return None
    return round(max(0.0, (base_cost - sc * d1) / d2), 2)


def target_report(inp: FeeInputs, target_pct: float | None) -> dict:
    """Одна відповідь для UI: gap + статус + ціна для досягнення цілі."""
    res = calculate(inp)
    report = gap_to_target(res.margin_pct, target_pct)
    report["price_needed"] = (
        price_for_target_margin(inp, target_pct)
        if target_pct is not None and target_pct > 0 else None
    )
    return report


__all__ = ["gap_to_target", "price_for_target_margin", "target_report"]
