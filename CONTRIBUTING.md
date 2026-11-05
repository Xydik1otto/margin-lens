# Contributing / Як долучитися до Margin Lens

Дякуємо за інтерес до Margin Lens! Цей документ — повна карта для
контриб'ютора: як влаштований проєкт, як підняти середовище, як додати
платформу, і які правила діють для комітів, гілок та мов.

**Мови комунікації: українська, English.** Російської локалізації в проєкті
немає і не буде (політичне рішення власника) — PR з нею не буде прийнято.

---

## 1. Як влаштований проєкт (архітектура)

Margin Lens — **офлайн SPA без бекенда** для розрахунку маржі та чистого
прибутку продавця маркетплейсів (Etsy, Shopify, Amazon, eBay, Vinted, Depop,
Poshmark). Ніякого сервера, бази даних чи збірки: відкрив `index.html` —
працює.

```
index.html            ← весь SPA: UI (vanilla JS, без фреймворків/бандлерів),
│                       розрахунки-дзеркало, словник I18N (UA/EN), ~1300 рядків
core/
│  fees.py            ← ДЖЕРЕЛО ПРАВДИ тарифів + уся розрахункова логіка
│  fees.generated.js  ← авто-згенероване JS-дзеркало констант (не редагувати!)
│  fx.py              ← конвертація валют (ставки ECB, офлайн-фолбек)
│  history.py         ← локальна історія розрахунків (localStorage)
│  dedupe.py          ← пошук схожих товарів між платформами
│  md_export.py       ← експорт звіту в Markdown
generate_js.py        ← генератор core/fees.generated.js з core/fees.py
scripts/
│  smoke.sh           ← 3-кроковий смоук: HTML-парсинг → pytest → синхронність JS
│  build-www.mjs      ← (гілка mobile/android-ios) бандл index.html + core/ у www/
tests/                ← ~211 тестів (деталі нижче)
android/, ios/        ← (гілка mobile/android-ios) Capacitor 7-проєкти
```

### Ключовий принцип: `core/fees.py` — джерело правди

Уся тарифна логіка живе в Python і покрита тестами, які **стверджують точні
числа**. SPA не рахує з «повітря»: константи тарифів експортуються з
`core/fees.py` у `core/fees.generated.js` командою `python generate_js.py`,
а `index.html` підключає цей файл тегом
`<script src="core/fees.generated.js">` — тому застосунок працює повністю
офлайн. JS-код усередині `index.html` залишає тонку логіку розрахунку
(з коментарями «JS mirror of …») — він дзеркалить функції з `core/fees.py`,
і числа в обох реалізаціях не можуть розійтися, бо за синхронністю стежать
смок-тест і сюїта.

Тарифні константи в `core/fees.py` (все в одному місці, з коментарем
«last verified YYYY-MM-DD» над кожним блоком):

- `ETSY` — listing / transaction / payment / offsite ads / ads / regulatory;
- `ETSY_REGIONAL` — payment processing по країнах продавця;
- `ETSY_SHIPPING_PRESETS` — типові ставки доставки по регіонах;
- `SHOPIFY`, `AMAZON_REFERRAL` + `AMAZON_PER_ITEM_FEE`, `EBAY`, `VINTED`,
  `DEPOP`, `POSMARK` + `POSMARK_FLAT_UNDER`.

Фіксовані збори, які платформи нараховує в USD (Etsy listing/payment,
Amazon per-item, eBay per-order), конвертуються у валюту продавця через
`core/fx.py` (`fixed_in_currency()`); відсотки — валюто-нейтральні.

### Структура тестів (`tests/`)

| Файл | Що покриває |
|---|---|
| `test_fees.py` | тарифи й розрахунки всіх платформ, breakeven, порівняння |
| `test_etsy_regional.py` | регіональні ставки payment processing Etsy |
| `test_depop_poshmark.py`, `test_ebay_vinted.py` | точні числа цих платформ |
| `test_currency.py`, `test_fx.py` | конвертація валют, курси, фолбек |
| `test_dedupe.py` | пошук схожих товарів |
| `test_history.py` | локальна історія |
| `test_md_export.py` | експорт звіту в Markdown |
| `test_i18n.py` | перемикач UA/EN, повнота пар у словнику `I18N` |
| `test_a11y.py` | доступність (aria-атрибути, клавіатура) |
| `test_privacy.py` | регресія витоків: без секретів/шляхів; **без російської** |

---

## 2. Середовище розробки

Потрібен лише Python 3.11+ (і `node` опційно — для `node --check` у smoke
та для мобільної збірки).

```bash
git clone https://github.com/Xydik1otto/margin-lens.git
cd margin-lens
git checkout -b feat/my-change        # ніколи не комітьте прямо в main

python -m venv .venv
source .venv/bin/activate             # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m pytest -q                   # уся сюїта (~211 тестів) — має бути зеленою
bash scripts/smoke.sh                 # HTML + тести + синхронність generated JS
```

Запуск застосунку: збірка не потрібна — відкрийте `index.html` у браузері
(або `python -m http.server` і `http://localhost:8000`, якщо зручніше).

`scripts/smoke.sh` — це те, що має пройти репозиторій перед деплоєм: він
парсить `index.html` як HTML, проганяє pytest і перевіряє, що
`core/fees.generated.js` синхронізований з `core/fees.py`.

---

## 3. Як додати нову платформу (покроково)

Це найцінніший тип внеску. Порядок суворий — кожен крок спирається на
попередній:

1. **`core/fees.py` — константи.** Додайте блок типу
   `NEWPLATFORM = {...}` із коментарем `# last verified YYYY-MM-DD` і
   посиланням на офіційну тарифну сторінку. Дотримуйтесь патерну сусідів:
   відсотки — як десяткові частки (`0.10`, не `10`), фіксовані USD-збори —
   окремими ключами.
2. **`core/fees.py` — функція розрахунку.** Додайте
   `newplatform_fees(inp: FeeInputs) -> dict` поруч із `vinted_fees`,
   `depop_fees` тощо, і підключіть платформу до `calculate()`,
   `_platform_pct_list()` та порівняння каналів — подивіться, як це зроблено
   для Depop/Poshmark (найпростіші приклади).
3. **Регенерація JS.** `python generate_js.py`
   (перевірка без запису: `python generate_js.py --check`).
   `core/fees.generated.js` руками не редагують.
4. **Тести.** Створіть `tests/test_newplatform.py` з точними числами
   (зразок: `tests/test_depop_poshmark.py`). Тести = документація тарифів:
   зміна ставки без оновлення тестів має червонити сюїту — це навмисно.
5. **UI (`index.html`).**
   - `<option value="newplatform">Назва</option>` у `<select id="platform">`;
   - гілки `inp.platform === "newplatform"` у JS-дзеркалах (орієнтир —
     пошук по `platform ===` у `index.html`: блоки тарифів, pay-pct,
     фіксованих зборів, breakeven);
   - специфічні поля вводу, якщо платформа їх потребує (див. Amazon
     `amazonCat`, Poshmark-тіри);
   - усі нові користувацькі тексти — **UA-оригінал + EN-ключ** у словнику
     `I18N` (тест `test_i18n.py` не пропустить непарні рядки);
   - aria-атрибут для нових інтерактивних елементів (тест `test_a11y.py`).
6. **Перевірка.** `python -m pytest -q && bash scripts/smoke.sh` — усе
   зелене.
7. **PR.** У описі — лінк на офіційну тарифну сторінку і дату перевірки.

Оновлення тарифів *існуючої* платформи — той самий цикл, мінус крок 5
(якщо UI не змінюється).

---

## 4. Коміти, гілки, PR

### Стиль комітів (Conventional Commits)

`тип: суть зміни` — коротко, в імперативі; українською або англійською
(обидві мови прийнятні, див. історію комітів):

```
feat:     нова функціональність        fix:      виправлення бага
docs:     тільки документація          test:     тільки тести
chore:    обслуговування/інфра         ci:       CI-воркфлоу
refactor: без зміни поведінки
```

Один логічний зміст = один коміт. Не мішайте логіку з docs; тарифна зміна
разом із тестами — це один коміт `feat:`/`fix:`.

### Модель гілок

- **`main` — стабільна гілка.** Кожен push у `main` автоматично деплоїть
  GitHub Pages (`.github/workflows/deploy.yml`). Тримайте `main` зеленим:
  `pytest` + `smoke.sh` перед кожним пушем.
- **`mobile/*` (наприклад `mobile/android-ios`) — мобільна розробка**
  (Capacitor: `android/`, `ios/`, `www/`, CI-збірки APK/.app). Мобільні
  коміти живуть тут, а не в `main`; злиття в `main` — тільки коли мобільні
  збірки зелені й зміни не ламають вебверсію.

### Процес PR

1. Гілка від свіжого `main`: `feat/<short-name>`, `fix/<short-name>`,
   `docs/<short-name>` тощо.
2. Локально зелені `python -m pytest -q` і `bash scripts/smoke.sh`.
3. PR у `main`: опис «що і чому»; для тарифних змін — джерело тарифів і
   дата перевірки.
4. Рев'ю власника; після мержу Pages оновиться автоматично.

Баг-репорти: шаблон `.github/ISSUE_TEMPLATE/bug_report.md` (укр/eng).
Фічі: спершу issue-обговорення (`feature_request.md`), потім код.
Безпека: [SECURITY.md](SECURITY.md) — не відкривайте публічний issue.

---

## 5. Правила i18n (мови)

- **Користувацькі тексти** в `index.html`: українська — оригінал і
  першоджерело; англійська — ключ у словнику `I18N` (перемикач мови,
  `localStorage`-ключ `ml_lang`). Тест `test_i18n.py` стежить, щоб кожен
  UA-рядок мав EN-пару.
- **Документація**: `README.md` / `CONTRIBUTING.md` (українською) +
  `README.en.md` / `CONTRIBUTING.en.md` (англійське дзеркало). Змінюєш одну
  мову — синхронізуй другу в тому самому PR.
- **Російська заборонена**: жодної російської локалізації, коментарів чи
  рядків — ніколи, у жодному файлі. Це політичне рішення власника, і воно
  не обговорюється знову; регресійний тест
  `tests/test_privacy.py::test_no_russian_in_documentation` стежить за
  документами. PR з російською локалізацією закриваються без обговорення.
- Жодних секретів, токенів, особистих даних чи локальних шляхів у комітах
  (теж перевіряється тестом).

---

## 6. Мобільна розробка (Android / iOS)

Мобільні застосунки — це та сама SPA, загорнута в Capacitor 7; сервер не
потрібен, усе офлайн. Повна інструкція — **[MOBILE.md](MOBILE.md)** на гілці
`mobile/android-ios`.

Коротко:

- **Android**: `android/` (minSdk 24, target/compile 35). Локально:
  `cd android && ./gradlew assembleDebug` → APK у `app/build/outputs/apk/`.
- **iOS**: `ios/` (Capacitor 7 через SPM, deployment target 14.0). Локально:
  відкрити Xcode-проєкт; збірка без підпису дає `.app` для sideload/AltStore.
- **CI** (на гілці `mobile/android-ios`): `android-build.yml` —
  `assembleDebug` APK → артефакт + attach до Release на тег; `ios-build.yml`
  — unsigned `.app` zip. Retention артефактів — 30 днів.
- Бандл для нативних оболонок готує `scripts/build-www.mjs`
  (`index.html` + `core/` → `www/`).
- **Важливо:** зміни логіки тарифів (`core/fees.py`) робіть спочатку в
  `main` через звичайний PR, потім оновіть мобільну гілку — не навпаки.

---

## Подяки

Кожен PR зі свіжими тарифами прямо економить комусь гроші — дякуємо, що
допомагаєте продавцям не переплачувати.
