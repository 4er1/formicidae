"""Convierte los hallazgos en tests Pytest reproducibles (el camino mínimo hacia cada bug)."""
from __future__ import annotations

import json
import os
import re

from .actions import Action

TESTABLE = {"http_error", "js_exception", "console_error", "request_failed", "broken_image", "error_text"}

CONFTEST = '''"""Fixtures para los tests generados por Formicidae."""
import os

import pytest
from playwright.sync_api import sync_playwright

from formicidae.detectors import Monitor


def pytest_configure(config):
    config.addinivalue_line("markers", "formicidae: test generado por Formicidae (reproduce un bug hallado)")


@pytest.fixture(scope="session")
def base_url():
    return os.environ.get("FORMICIDAE_BASE_URL", {base!r})


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture()
def page(browser):
    ctx = browser.new_context()
    pg = ctx.new_page()
    pg.set_default_timeout(8000)
    yield pg
    ctx.close()


@pytest.fixture()
def monitor(page, base_url):
    return Monitor(page, base_url)
'''

HEADER = '''"""Tests generados por Formicidae contra {base}
Cada test reproduce el camino mínimo hacia un hallazgo y FALLA mientras el bug exista."""
import pytest

from formicidae.actions import require, settle
'''


def case_name(i: int, signature: str) -> str:
    return f"test_bug_{i:02d}_" + re.sub(r"\W+", "_", signature).strip("_").lower()[:60]


def testable_sorted(result: dict) -> list[dict]:
    return sorted((r for r in result["findings"] if r["kind"] in TESTABLE),
                  key=lambda r: (-r["severity"], len(r["path"]), r["signature"]))


def render_tests(result: dict) -> tuple[str, list[str]]:
    recs = testable_sorted(result)
    out, names = [HEADER.format(base=result["base_url"])], []
    for i, r in enumerate(recs, 1):
        name = case_name(i, r["signature"])
        names.append(name)
        doc = json.dumps(r["signature"])[1:-1]
        out.append(f'\n\n@pytest.mark.formicidae\ndef {name}(page, monitor, base_url):')
        out.append(f'    """[sev {r["severity"]}] {doc} — visto {r["count"]}x, ruta mínima de {len(r["path"])} paso(s)."""')
        out.append("    page.goto(base_url)\n    settle(page)")
        for a in r["path"]:
            out.extend("    " + line for line in Action.from_dict(a).to_code())
        out.append("    monitor.scan_dom(page)")
        out.append(f"    monitor.assert_absent({r['signature']!r})")
    return "\n".join(out) + "\n", names


def write_tests(result: dict, out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    code, names = render_tests(result)
    with open(os.path.join(out_dir, "conftest.py"), "w", encoding="utf-8") as f:
        f.write(CONFTEST.replace("{base!r}", repr(result["base_url"])))
    with open(os.path.join(out_dir, "test_formicidae_bugs.py"), "w", encoding="utf-8") as f:
        f.write(code)
    return names
