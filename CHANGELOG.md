# Changelog

Усі значущі зміни проєкту документуються в цьому файлі.

Формат базується на [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
версіонування — [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed
- Монетизаційний scaffolding: `.github/FUNDING.yml` (Sponsors-кнопка), секцію
  «Монетизація» з PLAN.md (Freemium/Pro-тарифи, конверсія free→Pro), згадку
  FUNDING.yml у структурі README. Проєкт — **100% безкоштовний open-source**:
  усі фічі (batch CSV без лімітів, необмежені сценарії, export) доступні всім.

## [1.0.0] — 2026-11-05

### Added
- **Depop**: flat 10% від загальної суми продажу (товар + доставка покупця).
- **Poshmark**: комісія з ціни товару — $2.95 flat за товар < $15, 20% за $15+
  (breakeven розв'язується аналітично по обох тарифних рівнях — комісія має
  стрибок на межі $15).
- **Etsy regional variations**: payment processing залежить від країни продавця
  (`ETSY_REGIONAL`: US/GB/DE/FR/IT/ES/CA/AU — 3–4.5% + локальний fixed fee,
  UK = GB alias; невідома країна → базова ставка 3% + $0.25).
- **Batch-історія з трендом маржі** (`core/history.py`): прогони batch
  зберігаються в IndexedDB (store `batches`, fallback localStorage), список
  прогонів з видаленням, SVG-sparkline тренду середньої маржі
  (delta у п.п., up/down/flat).
- **Duplicate detection** (`core/dedupe.py`): однаковий товар (нормалізована
  назва: регістр/розділові знаки ігноруються, кирилиця підтримується)
  на кількох платформах групується; кнопка «⚖ Порівняти» — 1 клік переносить
  товар у вкладку «Порівняння каналів».
- **Copy as Markdown** (`core/md_export.py`): результати batch і порівняння
  каналів як GFM-таблиця в буфер обміну (escapes `|`, clipboard + fallback).
- **i18n UA/EN**: перемикач у шапці, JSON-словники, авто-детект
  `navigator.language`, збереження вибору (`ml_lang`), динамічні таблиці через
  `t()`, мова Markdown-експорту слідує UI. Російської локалізації немає
  (політичне рішення; закріплено тестами).
- **README.en.md** — англійський дзеркальний README для міжнародної аудиторії.
- **INSTALL.md** — покрокова інструкція для не-програміста: GitHub Pages
  (primary), локальний файл, автозапуск (Windows Startup / systemd user unit),
  оновлення, приватність.
- **A11y**: `:focus-visible` на всіх інтерактивних елементах, scenario-рядки
  як `role="button"` + `tabindex` з Enter/Space, aria-label на icon-кнопках,
  `aria-live` на асинхронних результатах.
- **OSS hygiene**: `CONTRIBUTING.md` (оновлення тарифів платформ — задокументований
  найчастіший зовнішній PR), issue-шаблони bug/feature (укр+eng), `SECURITY.md`,
  GitHub topics в README, privacy-регресія `tests/test_privacy.py`
  (шляхи/токени/персональні дані в repo відсутні), дати «last verified» біля
  всіх тарифних констант.

### Changed
- Порівняння каналів і CSV-експорт розширені до 7 платформ (eBay, Vinted,
  Depop, Poshmark + базові).
- Тести: 103 → 210 (+1 skipped).

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
