import pytest
from playwright.sync_api import sync_playwright

from formicidae.detectors import Monitor

HTML = "<html><body><img src='/missing.png'><script>nope()</script></body></html>"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def _page(browser):
    page = browser.new_context().new_page()

    def handler(route):
        url = route.request.url
        if url.endswith("/"):
            route.fulfill(status=200, content_type="text/html", body=HTML)
        elif url.endswith("/boom"):
            route.fulfill(status=500, body="x")
        else:
            route.fulfill(status=404, body="")

    page.route("**/*", handler)
    return page


def test_detecta_http_excepcion_js_e_imagen_rota(browser):
    page = _page(browser)
    mon = Monitor(page, "http://fake.test")
    page.goto("http://fake.test/")
    page.wait_for_timeout(200)
    mon.scan_dom(page)
    sigs = {f.signature for f in mon.found}
    assert "http_404 GET /missing.png" in sigs
    assert "broken_image /missing.png" in sigs
    assert any(s.startswith("js_exception ReferenceError") for s in sigs)


def test_detecta_500_e_ignora_favicon(browser):
    page = _page(browser)
    mon = Monitor(page, "http://fake.test")
    page.goto("http://fake.test/boom")
    page.evaluate("fetch('http://fake.test/favicon.ico').catch(() => 0)")
    page.wait_for_timeout(200)
    sigs = {f.signature for f in mon.found}
    assert "http_500 GET /boom" in sigs
    assert not any("favicon" in s for s in sigs)
    with pytest.raises(AssertionError):
        mon.assert_absent("http_500 GET /boom")
