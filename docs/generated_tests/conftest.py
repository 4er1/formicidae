"""Fixtures para los tests generados por Formicidae."""
import os

import pytest
from playwright.sync_api import sync_playwright

from formicidae.detectors import Monitor


def pytest_configure(config):
    config.addinivalue_line("markers", "formicidae: test generado por Formicidae (reproduce un bug hallado)")


@pytest.fixture(scope="session")
def base_url():
    return os.environ.get("FORMICIDAE_BASE_URL", 'http://127.0.0.1:5055')


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
