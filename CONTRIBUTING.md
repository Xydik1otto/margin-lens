# Contributing / Як долучитися

Дякуємо за інтерес до Margin Lens! Проєкт — офлайн SPA без бекенду; логіка зборів
у Python (`core/fees.py` — джерело правди), UI — vanilla JS в одному `index.html`.

Thanks for your interest in Margin Lens! It's an offline SPA with no backend:
fee logic lives in Python (`core/fees.py` — the source of truth), the UI is
vanilla JS in a single `index.html`.

**Мови комунікації / Languages: українська, English.** Російської локалізації
в проєкті немає і не буде (політичне рішення власника) — PR з нею не буде
прийнято. / Russian localization is intentionally out of scope.

---

## Найчастіший зовнішній PR: оновлення тарифів платформи / The most common PR: updating platform rates

Маркетплейси змінюють комісії кілька разів на рік. Це найкорисніший і
найпростіший внесок:

1. Знайдіть актуальну тарифну сторінку платформи (Etsy / Shopify / Amazon /
   eBay / Vinted / Depop / Poshmark) і зафіксуйте дату перевірки.
2. Відкрийте `core/fees.py` — усі константи в одному місці:
   - `ETSY` — listing/transaction/payment/offsite ads/ads/regulatory;
   - `ETSY_REGIONAL` — payment processing по країнах продавця;
   - `ETSY_SHIPPING_PRESETS` — типові ставки доставки по регіонах;
   - `SHOPIFY`, `AMAZON_REFERRAL` + `AMAZON_PER_ITEM_FEE`, `EBAY`, `VINTED`,
     `DEPOP`, `POSMARK` + `POSMARK_FLAT_UNDER`.
3. Оновіть константи **і** коментар «last verified …» над блоком.
4. Згенеруйте JS-константи: `python generate_js.py`
   (перевірка без запису: `python generate_js.py --check`).
5. Оновіть тести: вони asserting точні числа (наприклад,
   `tests/test_depop_poshmark.py`) — зміна тарифу без оновлення тестів
   червонить сюїту. Це навмисно: тести = документація тарифів.
6. `python -m pytest -q` + `bash scripts/smoke.sh` — усе зелене.
7. PR: у описі вкажіть лінк на офіційну тарифну сторінку і дату перевірки.

Marketplaces change fees several times a year — this is the easiest and most
valuable contribution. Edit the constants and the "last verified" comment in
`core/fees.py`, run `python generate_js.py`, update the exact-number tests,
make `pytest` + `scripts/smoke.sh` green, and reference the platform's public
fee page in your PR description.

## Інші типи внесків / Other contributions

- **Баг-репорти**: шаблон `.github/ISSUE_TEMPLATE/bug_report.md` (укр/eng).
- **Фічі**: спершу issue-обговорення (`feature_request.md`), потім код.
- **Безпека**: див. [SECURITY.md](SECURITY.md) — не відкривайте публічний issue.

## Технічні правила / Ground rules

1. **Один логічний коміт = один commit** (feat/fix/docs/chore).
2. Кожна фіча/зміна логіки — з тестами (`python -m pytest -q` зелений).
3. Тарифи змінюються **тільки** в `core/fees.py`; `core/fees.generated.js`
   не редагують руками (авто-генерація, тест стежить за синхронністю).
4. UI: без фреймворків і бандлерів; доступність (aria-label, клавіатура) —
   обов'язкова для нових інтерактивних елементів; тексти — UA (оригінал) +
   EN-ключ у словнику `I18N` в `index.html`.
5. Жодних секретів/токенів/локальних шляхів у комітах (перевіряється тестом).
6. Уaseline стилю: існуючі патерни проєкту (dataclass-логіка в `core/`,
   JS-mirrors з коментарем «JS mirror of …»).

## Локальний запуск / Local run

```bash
python -m pip install pytest
python -m pytest -q        # логіка
bash scripts/smoke.sh      # HTML + pytest + generated-JS sync (+ node --check)
```

SPA не потребує збірки: відкрийте `index.html` у браузері.
