# Changelog

Усі значущі зміни проєкту документуються в цьому файлі.

Формат базується на [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
версіонування — [SemVer](https://semver.org/spec/v2.0.0.html).

## [0.4.0] — 2026-11-05

### Added
- **Мультивалюта EUR/USD/GBP/UAH**: курси ECB (fetch + кеш 24 год у localStorage),
  офлайн-фолбек константами в `core/fx.py` (та в згенерованому `fees.generated.js`);
  фіксовані збори платформ (у USD) конвертуються у валюту продавця; символ валюти
  (€/$/£/₴) у всіх розрахунках, CSV-експорті, сценаріях та share-лінках.
- **eBay**: final value fee ~13.25% + $0.40 за замовлення (per order, не per unit).
- **Vinted**: 0% комісії продавця — buyer protection оплачує покупець;
  знижка на доставку моделюється через «ви платите».
- **Named presets сценаріїв**: перейменування (✎) та видалення (✕) збережених
  сценаріїв в IndexedDB (з fallback на localStorage).
- **Порівняльна діаграма**: SVG bar chart net profit по всіх 5 платформах
  у вкладці «Порівняння каналів» (zero-line при змішаних знаках).
- **Mobile polish**: media queries (≤600px — одна колонка, скрол табів),
  тап-зони ≥44px, інпути 16px без iOS zoom-on-focus.
- `CHANGELOG.md`, `FUNDING.yml`, favicon + OG-мета, `scripts/smoke.sh`.

### Changed
- `core/fees.py`: спільний helper `_platform_pct_list()` — один список відсоткових
  зборів для `calculate`, breakeven та ad_profit (без дублювання по платформах).
- `generate_js.py`: прапорець `--check` (верифікація синхронізації без запису).

## [0.3.0] — 2026-11-05

### Added
- Доставка Etsy: charged vs paid + регіональні пресети (у generated JS).
- Returns/refunds симуляція (% повернень → скоригований net/margin).
- Ad Profit calculator: ROAS, break-even ROAS, max прибутковий ad spend.
- IndexedDB-сховище сценаріїв (міграція з localStorage, fallback)
  + import/export JSON профілю (сценарії + batch CSV).

## [0.2.0] — 2026-11-05

### Added
- Shipping charged vs paid + маржа доставки в UI.
- Etsy Ads 12.5% + regulatory operating fee 0.32% (UK/FR/IT/ES).
- Ad-метрики: ROAS / break-even (v0.2.2).
- IndexedDB сценарії + import/export профілю (v0.2.3).

## [0.1.0-alpha] — 2026-11-05

### Added
- Калькулятор зборів: Etsy (listing/transaction/payment/offsite ads), Shopify
  (2.9% + $0.30 + підписка), Amazon (referral по категоріях, $0.99/товар).
- VAT/PDV, breakeven-ціна, слайдер «підняти ціну на X%».
- Batch CSV, side-by-side порівняння каналів, збережені сценарії.
- CSV-експорт, URL-share (`#p=base64`).
- JS-константи генеруються з Python (`generate_js.py` → `core/fees.generated.js`).
- GitHub Pages prep (LICENSE MIT, deploy.yml, .nojekyll).
