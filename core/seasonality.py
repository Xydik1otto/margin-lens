"""Сезонність продажів: орієнтовні індекси попиту по місяцях для типових ніш.

UI: вкладка «Сезонність» в index.html. Масив факторів експортується в
core/fees.generated.js (generate_js.py -> SEASONALITY), щоб SPA мав ті самі
числа офлайн.

Індекс ×1.0 = звичайний місяць; це ОЦІНКИ для планування (запаси/реклама),
не гарантія попиту. Джерело — загальновідома сезонність хендмейд-маркетплейсів
(Q4-пік, січневий спад, День святого Валентина/матері, весільний сезон).
"""

from __future__ import annotations

MONTHS_UA = ["Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень",
             "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень"]
MONTHS_EN = ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"]

#: Пороги рівнів попиту (у частках від звичайного місяця).
PEAK_THRESHOLD = 1.3
HIGH_THRESHOLD = 1.1
LOW_THRESHOLD = 0.8

SEASONALITY: dict[str, dict] = {
    "handmade_jewelry": {
        "label": "Прикраси (handmade)", "label_en": "Handmade jewelry",
        #                Січ  Лют  Бер  Кві  Тра  Чер  Лип  Сер  Вер  Жов  Лис  Гру
        "factors": [0.8, 1.5, 0.9, 0.9, 1.3, 1.0, 0.9, 0.9, 1.0, 1.1, 1.6, 1.9],
    },
    "candles_soap": {
        "label": "Свічки та мило", "label_en": "Candles & soap",
        "factors": [0.6, 0.7, 0.7, 0.7, 0.8, 0.7, 0.6, 0.7, 0.9, 1.3, 1.6, 1.9],
    },
    "christmas_decor": {
        "label": "Різдвяний декор", "label_en": "Christmas decor",
        "factors": [0.3, 0.4, 0.5, 0.5, 0.6, 0.6, 0.6, 0.8, 1.2, 1.7, 2.0, 1.6],
    },
    "apparel": {
        "label": "Одяг та аксесуари", "label_en": "Apparel & accessories",
        "factors": [0.8, 0.9, 1.0, 1.0, 1.1, 0.9, 0.9, 1.1, 1.2, 1.1, 1.4, 1.6],
    },
    "home_decor": {
        "label": "Декор для дому", "label_en": "Home decor",
        "factors": [1.1, 0.9, 0.8, 0.8, 0.9, 0.9, 0.8, 0.9, 1.1, 1.1, 1.3, 1.4],
    },
    "toys_kids": {
        "label": "Іграшки та дитячі товари", "label_en": "Toys & kids",
        "factors": [0.5, 0.7, 0.8, 0.9, 1.0, 0.9, 0.8, 0.9, 1.0, 1.2, 1.9, 2.2],
    },
    "wedding": {
        "label": "Весільна тематика", "label_en": "Wedding",
        "factors": [0.6, 0.8, 1.2, 1.4, 1.4, 1.5, 1.4, 1.3, 1.2, 0.9, 0.7, 0.6],
    },
    "digital_downloads": {
        "label": "Цифрові товари", "label_en": "Digital downloads",
        "factors": [1.1, 0.9, 0.9, 0.9, 0.9, 0.8, 0.8, 0.9, 1.0, 1.1, 1.4, 1.5],
    },
}

_NOTE_TEMPLATES = {
    "peak": {
        "ua": "{m} — піковий сезон (×{f}): найвищі продажі. Запаси, реклама й оновлені літинги — заздалегідь.",
        "en": "{m} is a peak month (×{f}): highest sales. Prepare stock, ads and refreshed listings early.",
    },
    "high": {
        "ua": "{m} — попит вище середнього (×{f}).",
        "en": "{m} — above-average demand (×{f}).",
    },
    "normal": {
        "ua": "{m} — звичайний попит (×{f}).",
        "en": "{m} — normal demand (×{f}).",
    },
    "low": {
        "ua": "{m} — низький сезон (×{f}): час готувати запаси, контент і літинги до піку.",
        "en": "{m} is the low season (×{f}): time to prepare stock, content and listings for the peak.",
    },
}


def seasonality_factor(category: str, month: int) -> float:
    """Індекс попиту для категорії в місяць (1-12). ValueError на ніші/місяці."""
    cat = SEASONALITY[category]  # unknown -> ValueError via KeyError wording below
    if not 1 <= int(month) <= 12:
        raise ValueError(f"month must be 1..12, got {month!r}")
    return cat["factors"][int(month) - 1]


def seasonality_level(factor: float) -> str:
    """"peak" | "high" | "normal" | "low" за індексом попиту."""
    if factor >= PEAK_THRESHOLD:
        return "peak"
    if factor >= HIGH_THRESHOLD:
        return "high"
    if factor <= LOW_THRESHOLD:
        return "low"
    return "normal"


def peak_months(category: str) -> list[int]:
    """Місяці (1-12) з індексом >= PEAK_THRESHOLD, за зростанням."""
    return [m for m in range(1, 13) if SEASONALITY[category]["factors"][m - 1] >= PEAK_THRESHOLD]


def quiet_months(category: str) -> list[int]:
    """Місяці (1-12) з індексом <= LOW_THRESHOLD, за зростанням."""
    return [m for m in range(1, 13) if SEASONALITY[category]["factors"][m - 1] <= LOW_THRESHOLD]


def seasonality_note(category: str, month: int, lang: str = "ua") -> dict:
    """Нотатка-підказка для UI: рівень, індекс і готовий текст.

    Returns::

        {
            "category", "month", "month_name_ua", "month_name_en",
            "factor", "level", "note",
        }
    """
    factor = seasonality_factor(category, month)
    level = seasonality_level(factor)
    m = int(month) - 1
    tpl = _NOTE_TEMPLATES[level][lang if lang in ("ua", "en") else "ua"]
    name = (MONTHS_EN if lang == "en" else MONTHS_UA)[m]
    return {
        "category": category,
        "month": int(month),
        "month_name_ua": MONTHS_UA[m],
        "month_name_en": MONTHS_EN[m],
        "factor": factor,
        "level": level,
        "note": tpl.replace("{m}", name).replace("{f}", f"{factor:.2f}"),
    }
