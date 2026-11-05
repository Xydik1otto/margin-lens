# Margin Lens — fee & real-margin calculator for Etsy/Shopify/Amazon/eBay/Vinted

![tests](https://img.shields.io/badge/tests-197%20passing-brightgreen) ![license](https://img.shields.io/badge/license-MIT-blue) ![version](https://img.shields.io/badge/version-1.0.0-orange)

**Live demo:** _placeholder — after push: `https://bigpi.github.io/margin-lens/`_ (GitHub Pages → Settings → Pages → Source: GitHub Actions)

> The Ukrainian original lives in [README.md](README.md). This file mirrors it for the international audience.

## Why this exists

> "A typical seller keeps **$18–20 of a $30 item** after all fees — and has **no idea** how much each channel is eating."

Before the MVP we researched sellers' pain points:

- **76 pay-signals** in e-commerce — fees are charged from everywhere: listing fee, transaction fee, payment processing, offsite ads, Etsy Ads, subscription, category referral. **Fee stacking** is the #1 seller complaint: no platform shows the combined picture.
- **No break-even point**: without the math you can't tell which channel wins, or at what price a sale stops making money.

Margin Lens exists to give the seller one honest number: **real net profit after all fees** — and to compare channels side-by-side before the item is ever listed.

## What it is

A **no-backend SPA**: vanilla JS + IndexedDB/localStorage, a single `index.html` — hosted on GitHub Pages for $0.

### Supported platforms (v1.0.0)

| Platform | Fee model |
|---|---|
| Etsy | 6.5% transaction + regional payment processing (3–4.5% + local fixed fee) + $0.20 listing; optional Offsite/Etsy Ads; 0.32% regulatory fee for GB/FR/IT/ES |
| Shopify | 2.9% + $0.30; monthly subscription spread over orders |
| Amazon | Referral by category (8–20%); $0.99/item on the individual plan |
| eBay | Final value ~13.25% + $0.40 per order |
| Vinted | 0% seller commission (buyer protection is on the buyer) |
| Depop | Flat 10% of the total sale |
| Poshmark | $2.95 flat under $15 item price, 20% at $15+ |

### Features

- **Calculator**: price, COGS, shipping (paid/charged), platform → every fee listed one by one (fee stacking made visible); net profit, margin %, breakeven price, "what if I raise the price by X%" slider
- **Multi-currency EUR/USD/GBP/UAH** — ECB rates (fetch + 24h cache, offline fallback)
- **Etsy regional variations** — payment processing by seller country (US/GB/DE/FR/IT/ES/CA/AU)
- **Batch mode** — paste a CSV list of products; runs are saved to **history (IndexedDB)** with a **margin trend sparkline**
- **Duplicate detection** — the same product on several platforms is grouped; **one-click comparison** across all channels
- **Copy as Markdown** — results/comparison as a GFM table for posts and reports
- **Side-by-side channel comparison** with an SVG bar chart
- **Ad Profit calculator** (Etsy Ads ROAS, break-even ROAS, max profitable spend)
- **Saved scenarios** (IndexedDB) with rename/delete, JSON profile import/export, URL-share links
- **UA/EN interface switcher** (auto-detects browser language, persists your choice)
- **Accessible**: aria-labels on interactive elements, keyboard navigation, visible focus states

The pure fee math lives in Python (`core/fees.py`), covered by tests; JS constants are **generated** from Python (`generate_js.py` → `core/fees.generated.js`) — the rates are never duplicated by hand.

## Quick start

The fastest way is the hosted page on GitHub Pages (see `INSTALL.md` for all options):

```bash
# SPA: just open the file
start index.html           # Windows (or open it in any browser)

# Fee-calculation tests
python -m pip install pytest
python -m pytest tests/ -v

# Smoke test (HTML parse + tests + generated-JS sync)
bash scripts/smoke.sh

# After changing rates in core/fees.py — regenerate the JS constants
python generate_js.py
```

## Updating platform rates (the most common external PR)

1. Open `core/fees.py` — it is the single source of truth.
2. Edit the constant block of the platform you are changing (`ETSY`, `SHOPIFY`, `AMAZON_REFERRAL`, `EBAY`, `VINTED`, `DEPOP`, `POSHMARK`, `ETSY_REGIONAL`) and update the "as of" year in the comment.
3. Run `python generate_js.py` to regenerate `core/fees.generated.js`.
4. Update/add tests — the suite asserts exact fee math, so a rate change without a test update will fail.
5. Run `bash scripts/smoke.sh` and `python -m pytest -q`.
6. Open a PR referencing the platform's public fee page.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

## Structure

```
margin-lens/
├── index.html              # SPA (calculator + batch + comparison + scenarios)
├── core/fees.py            # pure fee-calculation functions (source of truth)
├── core/fx.py              # multi-currency: ECB rates, cache, offline fallback
├── core/history.py         # batch history: margin trend + run summary
├── core/dedupe.py          # duplicate detection across platforms
├── core/md_export.py       # Markdown table export
├── core/fees.generated.js  # AUTO-GENERATED from fees.py (generate_js.py)
├── generate_js.py          # JS constants generator (--check to verify)
├── scripts/smoke.sh        # smoke: HTML parse + pytest + sync check
├── INSTALL.md              # step-by-step setup for non-programmers
├── CONTRIBUTING.md
├── CHANGELOG.md            # Keep a Changelog
├── .github/workflows/deploy.yml  # auto-deploy to GitHub Pages (push → main)
└── tests/
```

## Mobile apps (Android / iOS)

Margin Lens ships as a native shell (Capacitor 7) around the same SPA: the app bundles **the `index.html` itself + `core/`** — **fully offline, no server needed**. The APK is built in CI (`.github/workflows/android-build.yml`, minSdk 24 → target 35); iOS is an unsigned build for AltStore/Sideloadly (`ios-build.yml`, iOS 14+; the App Store requires Apple Developer at $99/year — not in budget). Downloads from [Releases](../../releases); install and local-build instructions — [MOBILE.md](MOBILE.md).

## Deploy

Push to `main` → the `deploy.yml` workflow publishes the static site to GitHub Pages (actions/deploy-pages@v4, no build step). `.nojekyll` disables Jekyll processing.

## Contributing

PRs are welcome — especially **platform rate updates** (see the section above). Bug reports and feature requests: use the issue templates. Security issues: see [SECURITY.md](SECURITY.md). Please keep contributions in Ukrainian or English.

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

Rates are taken from the platforms' public fee pages (last verified 2026-11-05; the date is documented in the `core/fees.py` comments) and change over time; update the constants in `core/fees.py` and run `python generate_js.py`. Exchange rates are indicative (ECB); the offline fallback constants are approximations.
