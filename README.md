# Margin Lens — калькулятор зборів та маржі для Etsy/Shopify/Amazon/eBay/Vinted

![tests](https://img.shields.io/badge/tests-197%20passing-brightgreen) ![license](https://img.shields.io/badge/license-MIT-blue) ![version](https://img.shields.io/badge/version-1.0.0-orange)

**English documentation:** [README.en.md](README.en.md)

**Live demo:** _плейсхолдер — після пушу: `https://bigpi.github.io/margin-lens/`_ (GitHub Pages → Settings → Pages → Source: GitHub Actions)

**Скріншот:** _плейсхолдер — `docs/screenshot.png` (додати пізніше)_

## Чому це існує

> «Типовий продавець отримує **$18–20 з товару за $30** після всіх зборів — і **не знає**, скільки саме «з'їдає» кожен канал.»

Перед MVP ми дослідили біль продавців маркетплейсів:

- **76 pay-сигналів** у e-commerce — збори стягуються звідусіль: listing fee, transaction fee, payment processing, offsite ads, Etsy Ads, підписка, referral по категоріях. **Fee stacking** (накопичення зборів) — головний біль продавців: жодна платформа не показує сумарну картинку.
- **Немає точки беззбитковості**: без розрахунку неможливо зрозуміти, який канал вигідніший і за якої ціни продаж перестає приносити гроші.

Margin Lens існує, щоб дати продавцю одне чесне число: **реальний net profit після всіх зборів** — і порівняти канали side-by-side до того, як товар виставлено.

## Що це

SPA **без бекенда**: vanilla JS + IndexedDB/localStorage, один `index.html` — розгорнуто на GitHub Pages за $0.

### v1.0.0 — готово для чужих користувачів

- **Depop** — flat 10% від загальної суми продажу
- **Poshmark** — $2.95 flat за товар < $15, 20% від ціни за $15+
- **Etsy regional variations** — payment processing по країні продавця (US/GB/DE/FR/IT/ES/CA/AU: 3–4.5% + локальний fixed fee)
- **Batch-історія з трендом маржі** — прогони зберігаються в IndexedDB, SVG-sparkline тренду середньої маржі (delta у п.п.)
- **Duplicate detection** — той самий товар на кількох платформах групується; порівняння в один клік
- **Copy as Markdown** — результати/порівняння як GFM-таблиця для постів і звітів
- **i18n UA/EN** — перемикач у UI, авто-детект мови браузера, збереження вибору
- **README.en.md + INSTALL.md** — англійська документація та покрокова інструкція для не-програміста
- **A11y** — focus-visible, клавіатурна навігація, aria-labels

### v0.4.0 — мультивалюта та нові платформи

- **Мультивалюта EUR/USD/GBP/UAH** — курси ECB (fetch + кеш 24 год, офлайн-фолбек константами); фіксовані збори конвертуються у вашу валюту
- **eBay** — final value fee ~13.25% + $0.40/замовлення
- **Vinted** — 0% комісії продавця (buyer protection оплачує покупець)
- **Named presets сценаріїв** — перейменування/видалення в IndexedDB
- **SVG bar chart** net profit у порівнянні каналів
- **Mobile polish** — тап-зони 44px, одна колонка, без iOS zoom

### Alpha-функції (v0.1.0-alpha)

- Калькулятор: ціна, собівартість, доставка (платите/платить покупець), платформа → всі збори по черзі (fee stacking наочно)
- **Etsy Ads (12.5%)** — опційний чекбокс
- **Regulatory operating fee (0.32%)** — автоматично для seller country UK/FR/IT/ES
- Shopify: 2.9% + $0.30, місячна підписка розмазана на замовлення
- Amazon: referral по категоріях (8–20%), $0.99/товар для індивідуального плану
- VAT/PDV % налаштовуваний
- Результат: **net profit, margin %, breakeven-ціна**, слайдер «а якщо підняти ціну на X%»
- Batch-режим: вставка CSV зі списком товарів
- Side-by-side порівняння каналів
- Збережені сценарії в localStorage
- **CSV-експорт** сценарію та порівняння каналів (кнопки ⬇)
- **URL-share**: кнопка 🔗 серіалізує сценарій в `#p=base64` → відкриття лінка відновлює всі параметри

### v0.3.0 — додаткові функції

- **Доставка Etsy: charged vs paid + регіональні ставки** — маржа доставки та пресети по регіонах
- **Returns/refunds симуляція** — % повернень → скоригована маржа
- **Ad profit calculator (Etsy Ads)** — break-even ROAS
- **IndexedDB** для великих batch-наборів + import/export JSON усього профілю

Чиста логіка розрахунку — у Python (`core/fees.py`), покрита тестами; JS-константи **генеруються** з Python (`generate_js.py` → `core/fees.generated.js`) — жодного дублювання тарифів.

## Швидкий старт

```bash
# SPA: просто відкрити файл
start index.html          # Windows (або відкрити в браузері)

# Тести розрахунку зборів
python -m pip install pytest
python -m pytest tests/ -v

# Smoke-тест (HTML + тести + синхронізація generated JS)
bash scripts/smoke.sh

# Після зміни тарифів у core/fees.py — регенерувати JS-константи
python generate_js.py
```

## Структура

```
margin-lens/
├── index.html              # SPA (калькулятор + batch + порівняння + сценарії)
├── core/fees.py            # чисті функції розрахунку зборів (джерело правди)
├── core/fx.py              # мультивалюта: курси ECB, кеш, офлайн-фолбек
├── core/history.py         # batch-історія: тренд маржі + summary прогонів
├── core/dedupe.py          # duplicate detection товару між платформами
├── core/md_export.py       # експорт результатів як Markdown-таблиця
├── core/fees.generated.js  # АВТО-ГЕНЕРОВАНО з fees.py (generate_js.py)
├── generate_js.py          # генератор JS-констант (--check для верифікації)
├── scripts/smoke.sh        # smoke: HTML parse + pytest + sync check
├── INSTALL.md              # покрокова інструкція для не-програміста
├── CONTRIBUTING.md         # як долучитися (тарифи — найчастіший PR)
├── CHANGELOG.md            # Keep a Changelog
├── .github/workflows/deploy.yml  # автодеплой на GitHub Pages (push → main)
└── tests/                  # test_fees, test_fx, test_currency, test_ebay_vinted,
                            # test_depop_poshmark, test_etsy_regional, test_history,
                            # test_dedupe, test_md_export, test_i18n, test_a11y
```

## Deploy

Push у `main` → workflow `deploy.yml` автоматично публікує статику на GitHub Pages (actions/deploy-pages@v4, без збірки). `.nojekyll` вимикає Jekyll-обробку.

## Contributing

PRs вітаються — **особливо оновлення тарифів платформ** (це найчастіший
зовнішній внесок): редагуєте константи в `core/fees.py` + коментар «last
verified», запускаєте `python generate_js.py`, оновлюєте exact-number тести,
`pytest` + `scripts/smoke.sh` зелені. Повна інструкція —
[CONTRIBUTING.md](CONTRIBUTING.md). Баги/фічі — через шаблони issue
(укр/eng); security — [SECURITY.md](SECURITY.md). Російська локалізація
не приймається.

**Рекомендовані GitHub topics** (Topics → редагувати в налаштуваннях репо):
`etsy` `shopify` `ebay` `vinted` `seller-tools` `ecommerce` `calculator` `github-pages`
(+ `depop` `poshmark` `margin-calculator` `fee-calculator` `vanilla-js` за бажанням)

## Дисклеймер

Тарифи — з відкритих тарифних сторінок платформ (остання перевірка: 2026-11-05, дати зазначені в коментарях `core/fees.py`) і змінюються платформами; оновлюйте константи в `core/fees.py` і запускайте `python generate_js.py`. Курси валют — довідкові (ECB); фолбек-константи — наближені.
