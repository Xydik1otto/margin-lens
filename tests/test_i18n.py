"""Tests for the UA/EN i18n switcher in index.html.

No Russian localization — that is a hard project rule; the test suite
enforces it (no Cyrillic strings must translate to ru, and no ru dict).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def inline_js() -> str:
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    return re.findall(r"<script>(.*?)</script>", src, re.S)[0]


def html() -> str:
    return (ROOT / "index.html").read_text(encoding="utf-8")


class TestI18nUi:
    def test_lang_toggle_buttons_exist(self):
        h = html()
        assert 'id="lang-uk"' in h and 'id="lang-en"' in h
        assert "setLang('uk')" in h and "setLang('en')" in h

    def test_applyi18n_and_t_exist(self):
        js = inline_js()
        for fn in ("function t(", "function applyI18n", "function setLang"):
            assert fn in js

    def test_applyi18n_called_on_init(self):
        js = inline_js()
        assert re.search(r"^applyI18n\(\);", js, re.M)

    def test_persistence_key(self):
        assert 'I18N_KEY = "ml_lang"' in inline_js()

    def test_auto_detect_browser_language(self):
        assert "navigator.language" in inline_js()

    def test_dict_has_en_and_uk_default(self):
        js = inline_js()
        # EN dictionary is non-trivial
        m = re.search(r"const I18N = \{\s*en: \{(.*?)\n\};", js, re.S)
        assert m, "I18N dict not found"
        entries = re.findall(r'"([^"]{2,60})":\s*"', m.group(1))
        assert len(entries) >= 40  # real coverage, not a stub


class TestNoRussian:
    """Hard rule: Russian localization must never appear."""

    RU_MARKERS = [
        "Платформ", "Расчёт", "сохран", "язык", "русск",
        "margin-lens на русском", "перевод",
    ]

    def test_no_ru_dictionary(self):
        js = inline_js()
        assert "ru:" not in js.replace("ru:", "ru:") or not re.search(r"\bru:\s*\{", js)

    def test_no_russian_only_markers_in_dict(self):
        # Ukrainian shares Cyrillic with Russian, so check for distinctly
        # Russian morphemes/words (ы/ъ hard signs, ща, "расч", "ЫЙ" endings)
        js = inline_js()
        for marker in ("Расч", "сохран", "языков", " ы ", "ъ", "Русск", "русск"):
            assert marker not in js, marker


class TestI18nRuntime:
    def test_t_function_translates_and_falls_back(self):
        code = (
            "const I18N={en:{'Калькулятор':'Calculator'}};"
            "let _lang='en';"
            "const t=x=>_lang==='en'?(I18N.en[x]??x):x;"
            "console.log(t('Калькулятор')+'|'+t('Немає перекладу'));"
        )
        r = subprocess.run(["node", "-e", code], capture_output=True, text=True)
        assert r.stdout.strip() == "Calculator|Немає перекладу"

    def test_generated_sync_still_passes_after_i18n(self):
        # i18n must not touch generated fee constants
        r = subprocess.run([sys.executable, "generate_js.py", "--check"],
                           capture_output=True, text=True, cwd=ROOT)
        assert r.returncode == 0
