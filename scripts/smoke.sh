#!/usr/bin/env bash
# Smoke-тест margin-lens (без бекенду — SPA):
#   1. index.html парситься як HTML і містить ключові елементи
#   2. python-тести розрахунку зборів зелені
#   3. core/fees.generated.js синхронізований з core/fees.py
# Виводить PASS/FAIL, exit code 0/1.
set -u
cd "$(dirname "$0")/.."
rc=0

echo "[1/3] index.html: parse + key elements"
python - <<'EOF' || rc=1
from html.parser import HTMLParser
import sys

src = open("index.html", encoding="utf-8").read()

class Checker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title = ""
        self.stack = []
        self.errors = []
        self.has_fees_script = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "script" and "fees.generated.js" in (attrs.get("src") or ""):
            self.has_fees_script = True
        if tag not in ("meta", "link", "br", "input", "img", "hr", "source"):
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append(f"mismatched </{tag}> (stack: {self.stack[-3:]})")

    def handle_data(self, data):
        if self.in_title:
            self.title += data

p = Checker()
p.feed(src)
p.close()

if p.errors:
    print("  HTML errors:", p.errors[:5]); sys.exit(1)
if p.stack:
    print("  unclosed tags:", p.stack[:5]); sys.exit(1)
if "Margin Lens" not in p.title.strip():
    print("  bad <title>:", p.title.strip()[:60]); sys.exit(1)
if not p.has_fees_script:
    print("  missing <script src=core/fees.generated.js>"); sys.exit(1)
print("  OK: title =", p.title.strip())
EOF

echo "[1b/3] inline <script> syntax (node --check, якщо node доступний)"
if command -v node >/dev/null 2>&1; then
  python - <<'EOF' || rc=1
import re, subprocess, sys, tempfile, os
src = open("index.html", encoding="utf-8").read()
scripts = re.findall(r"<script>(.*?)</script>", src, re.S)
ok = True
for i, code in enumerate(scripts):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(code); path = f.name
    r = subprocess.run(["node", "--check", path], capture_output=True, text=True)
    os.unlink(path)
    if r.returncode != 0:
        print(f"  JS syntax error in inline script #{i}:\n{r.stderr[:500]}")
        ok = False
if not ok: sys.exit(1)
print(f"  OK: {len(scripts)} inline script(s) parsed by node --check")
EOF
else
  echo "  SKIP: node не знайдено"
fi

echo "[2/3] pytest (fees/fx/currency/platforms)"
python -m pytest -q tests/ || rc=1

echo "[3/3] generated JS in sync"
python generate_js.py --check || rc=1

if [ "$rc" -eq 0 ]; then
  echo "SMOKE: PASS"
else
  echo "SMOKE: FAIL"
fi
exit "$rc"
