# Contributing to Margin Lens

Thanks for your interest in Margin Lens! This document is a full map for
contributors: how the project is structured, how to set up the environment,
how to add a platform, and which rules apply to commits, branches and
languages.

**Communication languages: Ukrainian, English.** There is no Russian
localization in this project and there never will be (an owner's political
decision) — PRs adding one will not be accepted.

---

## 1. Project architecture

Margin Lens is an **offline SPA with no backend** that computes margin and
net profit for marketplace sellers (Etsy, Shopify, Amazon, eBay, Vinted,
Depop, Poshmark). No server, no database, no build step: open `index.html`
and it works.

```
index.html            ← the whole SPA: UI (vanilla JS, no frameworks/bundlers),
│                       calculation mirrors, I18N dictionary (UA/EN), ~1300 lines
core/
│  fees.py            ← SOURCE OF TRUTH for fees + all calculation logic
│  fees.generated.js  ← auto-generated JS mirror of the constants (never edit!)
│  fx.py              ← currency conversion (ECB rates, offline fallback)
│  history.py         ← local calculation history (localStorage)
│  dedupe.py          ← cross-platform duplicate product detection
│  md_export.py       ← Markdown report export
generate_js.py        ← generates core/fees.generated.js from core/fees.py
scripts/
│  smoke.sh           ← 3-step smoke: HTML parse → pytest → JS sync check
│  build-www.mjs      ← (mobile/android-ios branch) bundles index.html + core/ into www/
tests/                ← ~211 tests (details below)
android/, ios/        ← (mobile/android-ios branch) Capacitor 7 projects
```

### Key principle: `core/fees.py` is the source of truth

All fee logic lives in Python and is covered by tests that **assert exact
numbers**. The SPA doesn't compute anything from thin air: fee constants are
exported from `core/fees.py` into `core/fees.generated.js` by running
`python generate_js.py`, and `index.html` loads that file with
`<script src="core/fees.generated.js">` — which is why the app works fully
offline. The JS inside `index.html` keeps only the thin calculation logic
(with "JS mirror of …" comments) — it mirrors the functions in
`core/fees.py`, and the numbers cannot drift apart because the smoke test
and the suite enforce sync.

Fee constants in `core/fees.py` (all in one place, each block carrying a
"last verified YYYY-MM-DD" comment):

- `ETSY` — listing / transaction / payment / offsite ads / ads / regulatory;
- `ETSY_REGIONAL` — payment processing by seller country;
- `ETSY_SHIPPING_PRESETS` — typical shipping rates by region;
- `SHOPIFY`, `AMAZON_REFERRAL` + `AMAZON_PER_ITEM_FEE`, `EBAY`, `VINTED`,
  `DEPOP`, `POSMARK` + `POSMARK_FLAT_UNDER`.

Fixed fees that platforms charge in USD (Etsy listing/payment, Amazon
per-item, eBay per-order) are converted to the seller's currency via
`core/fx.py` (`fixed_in_currency()`); percentages are currency-neutral.

### Test structure (`tests/`)

| File | Covers |
|---|---|
| `test_fees.py` | fees and calculations for all platforms, breakeven, comparison |
| `test_etsy_regional.py` | Etsy regional payment-processing rates |
| `test_depop_poshmark.py`, `test_ebay_vinted.py` | exact numbers for those platforms |
| `test_currency.py`, `test_fx.py` | currency conversion, rates, fallback |
| `test_dedupe.py` | duplicate product detection |
| `test_history.py` | local history |
| `test_md_export.py` | Markdown report export |
| `test_i18n.py` | UA/EN switcher, dictionary pair completeness |
| `test_a11y.py` | accessibility (aria attributes, keyboard) |
| `test_privacy.py` | leak regression: no secrets/paths; **no Russian** |

---

## 2. Development environment

You only need Python 3.11+ (and optionally `node` — for `node --check` in
smoke and for the mobile builds).

```bash
git clone https://github.com/Xydik1otto/margin-lens.git
cd margin-lens
git checkout -b feat/my-change        # never commit directly to main

python -m venv .venv
source .venv/bin/activate             # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m pytest -q                   # whole suite (~211 tests) must be green
bash scripts/smoke.sh                 # HTML + tests + generated-JS sync
```

Running the app: no build needed — open `index.html` in a browser (or
`python -m http.server` and `http://localhost:8000`, if you prefer).

`scripts/smoke.sh` is what the repo must pass before deploy: it parses
`index.html` as HTML, runs pytest, and checks that
`core/fees.generated.js` is in sync with `core/fees.py`.

---

## 3. How to add a new platform (step by step)

This is the most valuable kind of contribution. The order is strict — each
step builds on the previous one:

1. **`core/fees.py` — constants.** Add a block like `NEWPLATFORM = {...}`
   with a `# last verified YYYY-MM-DD` comment and a link to the platform's
   official fee page. Follow the neighbors' pattern: percentages as decimal
   fractions (`0.10`, not `10`), fixed USD fees as separate keys.
2. **`core/fees.py` — calculation function.** Add
   `newplatform_fees(inp: FeeInputs) -> dict` next to `vinted_fees`,
   `depop_fees`, etc., and wire the platform into `calculate()`,
   `_platform_pct_list()` and the channel comparison — see how
   Depop/Poshmark are wired (the simplest examples).
3. **Regenerate JS.** `python generate_js.py`
   (dry check: `python generate_js.py --check`).
   `core/fees.generated.js` is never edited by hand.
4. **Tests.** Create `tests/test_newplatform.py` with exact numbers
   (template: `tests/test_depop_poshmark.py`). Tests are the fee
   documentation: a rate change without a test update must turn the suite
   red — that's intentional.
5. **UI (`index.html`).**
   - `<option value="newplatform">Name</option>` in
     `<select id="platform">`;
   - `inp.platform === "newplatform"` branches in the JS mirrors
     (landmark: search for `platform ===` in `index.html` — fee blocks,
     pay-pct, fixed fees, breakeven);
   - platform-specific input fields if needed (see Amazon `amazonCat`,
     Poshmark tiers);
   - every new user-facing string — **UA original + EN key** in the `I18N`
     dictionary (test `test_i18n.py` rejects unpaired strings);
   - aria attributes for new interactive elements (test `test_a11y.py`).
6. **Verify.** `python -m pytest -q && bash scripts/smoke.sh` — all green.
7. **PR.** In the description: a link to the official fee page and the date
   verified.

Updating rates of an *existing* platform is the same cycle minus step 5
(unless the UI changes).

---

## 4. Commits, branches, PRs

### Commit style (Conventional Commits)

`type: what changed` — short, imperative, in the commit's language
(Ukrainian or English — both are fine, see the commit history):

```
feat:     new functionality            fix:      bug fix
docs:     documentation only           test:     tests only
chore:    maintenance/infra            ci:       CI workflow
refactor: no behavior change
```

One logical change = one commit. Don't mix logic with docs; a fee change
together with its tests is a single `feat:`/`fix:` commit.

### Branching model

- **`main` is the stable branch.** Every push to `main` automatically
  deploys GitHub Pages (`.github/workflows/deploy.yml`). Keep `main` green:
  `pytest` + `smoke.sh` before every push.
- **`mobile/*` (e.g. `mobile/android-ios`) is mobile development**
  (Capacitor: `android/`, `ios/`, `www/`, CI builds for APK/.app). Mobile
  commits live here, not in `main`; merging into `main` happens only when
  the mobile builds are green and the web version is unaffected.

### PR process

1. Branch off a fresh `main`: `feat/<short-name>`, `fix/<short-name>`,
   `docs/<short-name>`, etc.
2. Locally green `python -m pytest -q` and `bash scripts/smoke.sh`.
3. PR into `main`: describe what and why; for fee changes — the fee source
   and the verification date.
4. Owner review; after merge, Pages updates automatically.

Bug reports: the `.github/ISSUE_TEMPLATE/bug_report.md` template (UA/EN).
Features: discuss in an issue first (`feature_request.md`), then code.
Security: see [SECURITY.md](SECURITY.md) — do not open a public issue.

---

## 5. i18n rules

- **User-facing strings** in `index.html`: Ukrainian is the original and
  the source of truth; English lives as keys in the `I18N` dictionary
  (language switcher, `localStorage` key `ml_lang`). Test `test_i18n.py`
  enforces that every UA string has an EN pair.
- **Documentation**: `README.md` / `CONTRIBUTING.md` (Ukrainian) +
  `README.en.md` / `CONTRIBUTING.en.md` (English mirror). If you change one
  language, sync the other in the same PR.
- **Russian is banned**: no Russian localization, comments or strings —
  ever, in any file. This is the owner's political decision and it is not
  up for renegotiation; the regression test
  `tests/test_privacy.py::test_no_russian_in_documentation` watches the
  docs. PRs adding Russian localization are closed without discussion.
- No secrets, tokens, personal data or local paths in commits (also
  enforced by a test).

---

## 6. Mobile development (Android / iOS)

The mobile apps are the same SPA wrapped in Capacitor 7; no server needed,
fully offline. The full guide is **[MOBILE.md](MOBILE.md)** on the
`mobile/android-ios` branch.

In short:

- **Android**: `android/` (minSdk 24, target/compile 35). Locally:
  `cd android && ./gradlew assembleDebug` → APK in `app/build/outputs/apk/`.
- **iOS**: `ios/` (Capacitor 7 via SPM, deployment target 14.0). Locally:
  open the Xcode project; an unsigned build yields a `.app` for
  sideload/AltStore.
- **CI** (on the `mobile/android-ios` branch): `android-build.yml` —
  `assembleDebug` APK → artifact + attach to the Release on a tag;
  `ios-build.yml` — unsigned `.app` zip. Artifact retention: 30 days.
- The bundle for the native shells is prepared by `scripts/build-www.mjs`
  (`index.html` + `core/` → `www/`).
- **Important:** fee-logic changes (`core/fees.py`) go into `main` first via
  a regular PR, then the mobile branch is updated — never the other way
  around.

---

## Thanks

Every PR with fresh fee rates directly saves someone money — thank you for
helping sellers stop overpaying.
