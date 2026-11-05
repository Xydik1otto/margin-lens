# INSTALL — Margin Lens для не-програміста

Мета: ви відкриваєте калькулятор за **5 хвилин**, без знання коду. Оберіть ОДИН варіант:

- **Варіант А — GitHub Pages (рекомендовано, primary)**: нічого встановлювати, просто лінк у браузері.
- **Варіант Б — локальний файл**: відкрити `index.html` з диска (працює офлайн).
- **Варіант В — для розробника**: тести + регенерація констант.

---

## Варіант А. GitHub Pages (primary)

1. Відкрийте в браузері: **https://bigpi.github.io/margin-lens/**
2. Готово. Інтерфейс авто-визначить мову (UA/EN) — перемикач «UA / EN» у правому верхньому куті.
3. Дані (сценарії, історія batch-прогонів) зберігаються **у вашому браузері** (IndexedDB) —
   нічого не надсилається на сервер. Очищення даних браузера = втрата сценаріїв, тому раз на
   час робіть «⬇ Експорт профілю (JSON)» у вкладці «Сценарії».

Оновлення: сторінка оновлюється автоматично при кожному push в `main` (GitHub Actions).

Якщо ви хочете **власну копію** Pages-сторінки (свій GitHub акаунт):

1. Зареєструйтесь на github.com → кнопка **Fork** на `bigpi/margin-lens`.
2. У форку: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Все — ваш лінк: `https://<ваш-нік>.github.io/margin-lens/` (деплой займає ~1 хвилину).

## Варіант Б. Локальний файл (Windows / macOS / Linux)

1. Завантажте репозиторій: зелена кнопка **Code → Download ZIP** на сторінці
   `https://github.com/bigpi/margin-lens`, розпакуйте ZIP.
2. Відкрийте папку і подвійний клік на **`index.html`** — відкриється в браузері.
3. Все. Інтернет не потрібен: курси валют працюють офлайн (вбудовані фолбек-константи).

> Не переміщуйте `index.html` окремо від папки `core/` — файл читає `core/fees.generated.js`.

### Автозапуск (опційно, Windows)

Щоб калькулятор відкривався при вході в систему:

1. Натисніть `Win + R`, введіть `shell:startup`, Enter.
2. Скопіюйте туди **ярлик** на `index.html` (правий клік на файлі → «Надіслати» → «Робочий стіл (створити ярлик)», потім перемістіть ярлик у папку Startup).

### Автозапуск (опційно, Linux — systemd user unit)

Створіть файл `~/.config/systemd/user/margin-lens.service`:

```ini
[Unit]
Description=Margin Lens static SPA (local file)
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/usr/bin/xdg-open /opt/margin-lens/index.html

[Install]
WantedBy=graphical-session.target
```

Потім: `systemctl --user enable --now margin-lens.service`
(скопіюйте репозиторій у `/opt/margin-lens` або виправте шлях).

## Варіант В. Для розробника

Потрібен Python 3.10+ (для тестів; самому калькулятору Python не потрібен).

```bash
git clone https://github.com/bigpi/margin-lens.git
cd margin-lens
python -m pip install pytest
python -m pytest -q            # 197 тестів логіки зборів
bash scripts/smoke.sh          # HTML + тести + синхронізація generated JS
```

Зміна тарифів платформ:

```bash
# 1) редагуєте константи в core/fees.py
python generate_js.py          # 2) регенерує core/fees.generated.js
python -m pytest -q            # 3) зелені тести
```

## Оновлення встановленої копії

- **GitHub Pages (А)**: нічого робити — оновлюється сам.
- **Локальний файл (Б)**: завантажте новий ZIP і замініть папку; ваші дані в браузері
  (IndexedDB) не стираються — вони прив'язані до адреси/файлу, а не до версії.
- **Розробник (В)**: `git pull` → `python generate_js.py --check` → `pytest`.

## Приватність

- Ніякого бекенду, ніякої аналітики, ніяких cookies-трекерів.
- Єдиний мережевий запит — курси валют з ECB (ecb.europa.eu), раз на 24 години; без інтернету працює офлайн.
- Єдиний зовнішній файл на сторінці — згенерований `core/fees.generated.js` з вашого ж диска.
