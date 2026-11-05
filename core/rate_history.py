"""Історія змін тарифів платформ з датами — датгований журнал змін.

UI: вкладка «Історія тарифів» в index.html (дані експортуються в
core/fees.generated.js як RATE_HISTORY). Журнал ведеться вручну на основі
публічних анонсів платформ; дати — ефективні (не дати анонсів).

Це відповідь на ризик з PLAN.md розділ 6: «Платформи змінюють тарифи →
застарілі розрахунки». При зміні констант у core/fees.py додайте запис сюди
і запустіть ``python generate_js.py`` (обов'язково при будь-якій зміні
тарифів — тести перевіряють синхронізацію).
"""

from __future__ import annotations

from datetime import date

#: Платформи, які модельує калькулятор (порядок відображення).
PLATFORMS = ("etsy", "shopify", "amazon", "ebay", "vinted", "depop", "poshmark")

RATE_HISTORY: list[dict] = [
    {
        "date": "2018-07-02",
        "platform": "etsy",
        "ua": "Transaction fee: 3.5% → 5%",
        "en": "Transaction fee: 3.5% → 5%",
    },
    {
        "date": "2022-04-11",
        "platform": "etsy",
        "ua": "Transaction fee: 5% → 6.5% (база: ціна + доставка покупця)",
        "en": "Transaction fee: 5% → 6.5% (base: item + customer-paid shipping)",
    },
    {
        "date": "2023-02-15",
        "platform": "ebay",
        "ua": "Final value fee: 12.9% → 13.25% для більшості категорій (США)",
        "en": "Final value fee: 12.9% → 13.25% in most categories (US)",
    },
    {
        "date": "2023-06-01",
        "platform": "etsy",
        "ua": "Regulatory operating fee: UK 0.25% → 0.32%, Італія 0.25% → 0.32%, Франція 0.40% → 0.47%",
        "en": "Regulatory operating fee: UK 0.25% → 0.32%, Italy 0.25% → 0.32%, France 0.40% → 0.47%",
    },
    {
        "date": "2024-07-15",
        "platform": "depop",
        "ua": "США: скасовано 10% комісію продавця (USD-продажі). Калькулятор поки застосовує 10% до всіх ринків — для США беріть це до уваги",
        "en": "US: 10% selling fee removed (USD sales). The calculator still applies 10% to all markets — factor this in for US sales",
    },
]


def _sorted_desc(entries: list[dict]) -> list[dict]:
    return sorted(entries, key=lambda e: e["date"], reverse=True)


def changes_for(platform: str) -> list[dict]:
    """Записи журналу для платформи, від найсвіжішої до найстарішої."""
    p = (platform or "").strip().lower()
    if p not in PLATFORMS:
        raise ValueError(f"unknown platform: {platform!r}")
    return _sorted_desc([e for e in RATE_HISTORY if e["platform"] == p])


def last_change(platform: str) -> dict | None:
    """Найсвіжіша зміна тарифу платформи (None — змін не зафіксовано)."""
    entries = changes_for(platform)
    return entries[0] if entries else None


def platforms_with_history() -> list[str]:
    """Платформи, для яких є хоч один запис у журналі."""
    return [p for p in PLATFORMS if any(e["platform"] == p for e in RATE_HISTORY)]


def platforms_without_history() -> list[str]:
    """Платформи без записів — тариф вважається незмінним з запуску калькулятора."""
    return [p for p in PLATFORMS if not any(e["platform"] == p for e in RATE_HISTORY)]


def format_changes(platform: str | None = None, lang: str = "ua") -> list[str]:
    """Готові рядки для UI: «YYYY-MM-DD — зміна» (з [платформа] для всіх разом)."""
    entries = (_sorted_desc(list(RATE_HISTORY)) if platform is None
               else changes_for(platform))
    lines = []
    for e in entries:
        text = e.get(lang if lang in ("ua", "en") else "ua", "")
        prefix = f"{e['date']} [{e['platform']}] — " if platform is None \
            else f"{e['date']} — "
        lines.append(prefix + text)
    return lines
