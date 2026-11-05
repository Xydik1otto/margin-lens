# Security Policy / Політика безпеки

## Підтримувані версії / Supported versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ так / yes |
| < 1.0   | ❌ ні / no |

## Як повідомити / How to report

**Не відкривайте публічний issue для security-проблем.** / Do not open a public
issue for security problems.

Використовуйте GitHub **Private vulnerability reporting** (вкладка «Security»
репозиторію → «Report a vulnerability») або напишіть власнику репозиторію
напрямку через GitHub. Use GitHub's private vulnerability reporting or contact
the repository owner directly via GitHub.

Відповідь — протягом 7 днів. / Response within 7 days.

## Що в межах / In scope

- Витік даних користувача за межі пристрою (SPA має працювати локально;
  єдиний дозволений зовнішній запит — курси валют з `ecb.europa.eu`).
- XSS через введення користувача (назви товарів, CSV, share-лінки `#p=...`,
  імпорт JSON-профілю) — будь-яке потрапляння неконтрольованого HTML у DOM.
- Пошкодження/втрата даних у IndexedDB/localStorage без дії користувача.
- Supply-chain: компрометація залежностей (їх немає — vanilla JS/Python stdlib,
  і це частина моделі безпеки).

## Поза межами / Out of scope

- «Клієнт може підмінити собі числа в localStorage» — дані не залишають
  пристрій, довіряти їм має лише сам користувач.
- Відсутність CSP/SRI-заголовків на GitHub Pages (платформенне обмеження;
  пул-реквести з коректним CSP-мета-тегом вітаються).
- Фізичний доступ до пристрою користувача.

## Приватність / Privacy

Проєкт не збирає жодних даних: немає бекенду, аналітики, cookies-трекерів.
Сценарії, batch-історія і кеш курсів зберігаються лише у браузері користувача.
