# 📱 Margin Lens на телефоні (Android / iOS)

> **English:** see [English section](#english) below.

## Українською

Margin Lens — **SPA без бекенда**: застосунок бандлить **сам `index.html`**
(+ згенеровані константи тарифів `core/fees.generated.js`) у APK/IPA.
**Повністю офлайн, сервер не потрібен** — адреса сервера не налаштовується,
бо її не існує. Розрахунки виконуються на телефоні; курси валют ECB —
онлайн-оновлення з офлайн-фолбеком константами (без інтернету працює все,
окрім свіжих курсів).

### Як скачати (найпростіший шлях)

1. Відкрийте [Releases](../../releases) цього репозиторію.
2. Завантажте:
   - **Android**: `app-debug.apk` (артефакт CI-збірки на кожен push; на тегі
     `v*` APK прикріплюється до Release).
   - **iOS**: `margin-lens-ios-unsigned.zip` (unsigned `.app` для
     AltStore/Sideloadly).
3. Встановіть (див. нижче).

### Android — встановлення APK (sideload, безкоштовно)

1. Скачайте `app-debug.apk` на телефон.
2. Дозвольте «Встановлення невідомих застосунків» для вашого файлового
   менеджера (Налаштування → Безпека).
3. Відкрийте APK → Встановити. Android 7.0+ (minSdk 24) — підтримується.

### iOS — AltStore / Sideloadly (безкоштовно, без Apple Developer)

App Store вимагає Apple Developer ($99/рік) — цього немає в бюджеті проєкту,
тому офіційної публікації в App Store не буде. Шлях:

1. Скачайте `margin-lens-ios-unsigned.zip`, розпакуйте — всередині `App.app`.
2. Через [AltStore](https://altstore.io) або
   [Sideloadly](https://sideloadly.io) підпишіть і встановіть на телефон
   безкоштовним Apple ID.
3. Безкоштовний сертифікат живе **7 днів** — re-sign потрібно повторювати.
   (Пізніше можливий TestFlight.)

### Збірка локально

```bash
npm install
npm run build        # www/ = index.html + core/ (з кореня репо)
npx cap copy android # веб-асети в android/app/src/main/assets/public
cd android && ./gradlew assembleDebug   # потрібен Android SDK
# APK: android/app/build/outputs/apk/debug/app-debug.apk
```

iOS — тільки на macOS (Xcode 16+, iOS 14+): `npx cap copy ios`, потім
`xcodebuild build -project ios/App/App.xcodeproj -scheme App -sdk iphoneos`.

### CI-збірки

- `.github/workflows/android-build.yml` — ubuntu, JDK 17, `assembleDebug` →
  APK-артефакт (retention 30 днів) на кожен push + attach до Release на тег.
- `.github/workflows/ios-build.yml` — macos, `xcodebuild` (unsigned,
  `CODE_SIGNING_ALLOWED=NO`) → zip `.app` (retention 30 днів).

### Деталі

- appId: `io.github.xydik1otto.margin-lens` (в Android-нативному коді —
  валідний для Java варіант `io.github.xydik1otto.margin_lens`: дефіс у
  Java-пакеті не компілюється; iOS bundle id — з дефісом, як задано).
- Android: minSdk 24 (Android 7.0) → targetSdk 35; дозвіл — лише INTERNET
  (для оновлення курсів ECB; без нього застосунок теж працює).
- iOS: deployment target 14.0, збірка без підпису.
- Оновлення тарифів: зміни в `core/fees.py` → `python generate_js.py` →
  нова збірка застосунку (константи вшиті в бандл).

---

## English

Margin Lens is a **backend-less SPA**: the app bundles **the `index.html`
itself** (+ generated fee constants `core/fees.generated.js`) into APK/IPA.
**Fully offline, no server needed** — there is no server URL to configure.
All calculations run on the phone; ECB exchange rates refresh online with an
offline fallback (everything except fresh rates works without internet).

### Download (easiest path)

1. Open this repo's [Releases](../../releases) page.
2. Grab:
   - **Android**: `app-debug.apk` (CI artifact on every push; attached to the
     Release on `v*` tags).
   - **iOS**: `margin-lens-ios-unsigned.zip` (unsigned `.app` for
     AltStore/Sideloadly).
3. Install (see below).

### Android — sideload install (free)

1. Download `app-debug.apk` on the phone.
2. Allow "Install unknown apps" for your file manager (Settings → Security).
3. Open the APK → Install. Android 7.0+ (minSdk 24) is supported.

### iOS — AltStore / Sideloadly (free, no Apple Developer account)

The App Store requires Apple Developer ($99/year) — out of the project's
budget, so there is no App Store release. The path:

1. Download `margin-lens-ios-unsigned.zip`, unpack — inside is `App.app`.
2. Use [AltStore](https://altstore.io) or
   [Sideloadly](https://sideloadly.io) to sign and install with a free
   Apple ID.
3. The free certificate lasts **7 days** — re-signing must be repeated.
   (TestFlight may come later.)

### Build locally

```bash
npm install
npm run build        # www/ = index.html + core/ (from repo root)
npx cap copy android # web assets into android/app/src/main/assets/public
cd android && ./gradlew assembleDebug   # requires the Android SDK
# APK: android/app/build/outputs/apk/debug/app-debug.apk
```

iOS is macOS-only (Xcode 16+, iOS 14+): `npx cap copy ios`, then
`xcodebuild build -project ios/App/App.xcodeproj -scheme App -sdk iphoneos`.

### CI builds

- `.github/workflows/android-build.yml` — ubuntu, JDK 17, `assembleDebug` →
  APK artifact (30-day retention) on every push + attached to the Release on
  tags.
- `.github/workflows/ios-build.yml` — macOS, `xcodebuild` (unsigned,
  `CODE_SIGNING_ALLOWED=NO`) → zipped `.app` (30-day retention).

### Details

- appId: `io.github.xydik1otto.margin-lens` (the Android native code uses the
  Java-valid variant `io.github.xydik1otto.margin_lens` — hyphens are invalid
  in Java packages; the iOS bundle id keeps the hyphen as specified).
- Android: minSdk 24 (Android 7.0) → targetSdk 35; the only permission is
  INTERNET (for ECB rate refresh — the app works without it too).
- iOS: deployment target 14.0, unsigned build.
- Fee-rate updates: edit `core/fees.py` → `python generate_js.py` → rebuild
  the app (constants are baked into the bundle).
