"""Tests generados por Formicidae contra http://127.0.0.1:5055
Cada test reproduce el camino mínimo hacia un hallazgo y FALLA mientras el bug exista."""
import pytest

from formicidae.actions import require, settle



@pytest.mark.formicidae
def test_bug_01_http_500_get_search(page, monitor, base_url):
    """[sev 5] http_500 GET /search — visto 3x, ruta mínima de 2 paso(s)."""
    page.goto(base_url)
    settle(page)
    require(page, 'a[href="/search"]:visible')
    page.locator('a[href="/search"]:visible').first.click()
    settle(page)
    require(page, 'form[action="/search"]')
    require(page, 'form[action="/search"] >> [name="q"]')
    page.locator('form[action="/search"] >> [name="q"]').first.fill("' OR '1'='1")
    page.locator('form[action="/search"]').first.evaluate("f => f.requestSubmit()")
    settle(page)
    monitor.scan_dom(page)
    monitor.assert_absent('http_500 GET /search')


@pytest.mark.formicidae
def test_bug_02_http_500_get_products_7_reviews(page, monitor, base_url):
    """[sev 5] http_500 GET /products/7/reviews — visto 1x, ruta mínima de 3 paso(s)."""
    page.goto(base_url)
    settle(page)
    require(page, 'a[href="/products"]:visible')
    page.locator('a[href="/products"]:visible').first.click()
    settle(page)
    require(page, 'a[href="/products/7"]:visible')
    page.locator('a[href="/products/7"]:visible').first.click()
    settle(page)
    require(page, 'a[href="/products/7/reviews"]:visible')
    page.locator('a[href="/products/7/reviews"]:visible').first.click()
    settle(page)
    monitor.scan_dom(page)
    monitor.assert_absent('http_500 GET /products/7/reviews')


@pytest.mark.formicidae
def test_bug_03_http_500_post_cart_add(page, monitor, base_url):
    """[sev 5] http_500 POST /cart/add — visto 2x, ruta mínima de 3 paso(s)."""
    page.goto(base_url)
    settle(page)
    require(page, 'a[href="/products"]:visible')
    page.locator('a[href="/products"]:visible').first.click()
    settle(page)
    require(page, 'a[href="/products/7"]:visible')
    page.locator('a[href="/products/7"]:visible').first.click()
    settle(page)
    require(page, 'form[action="/cart/add"]')
    require(page, 'form[action="/cart/add"] >> [name="qty"]')
    page.locator('form[action="/cart/add"] >> [name="qty"]').first.fill('-1')
    page.locator('form[action="/cart/add"]').first.evaluate("f => f.requestSubmit()")
    settle(page)
    monitor.scan_dom(page)
    monitor.assert_absent('http_500 POST /cart/add')


@pytest.mark.formicidae
def test_bug_04_js_exception_referenceerror_sendmessage_is_not_defined(page, monitor, base_url):
    """[sev 4] js_exception ReferenceError: sendMessage is not defined — visto 20x, ruta mínima de 2 paso(s)."""
    page.goto(base_url)
    settle(page)
    require(page, 'a[href="/contact"]:visible')
    page.locator('a[href="/contact"]:visible').first.click()
    settle(page)
    require(page, 'button:has-text("Enviar mensaje"):visible')
    page.locator('button:has-text("Enviar mensaje"):visible').first.click()
    settle(page)
    monitor.scan_dom(page)
    monitor.assert_absent('js_exception ReferenceError: sendMessage is not defined')


@pytest.mark.formicidae
def test_bug_05_console_error_config_de_faq_no_cargada(page, monitor, base_url):
    """[sev 2] console_error Config de FAQ no cargada — visto 20x, ruta mínima de 1 paso(s)."""
    page.goto(base_url)
    settle(page)
    require(page, 'a[href="/faq"]:visible')
    page.locator('a[href="/faq"]:visible').first.click()
    settle(page)
    monitor.scan_dom(page)
    monitor.assert_absent('console_error Config de FAQ no cargada')


@pytest.mark.formicidae
def test_bug_06_http_404_get_static_team_png(page, monitor, base_url):
    """[sev 2] http_404 GET /static/team.png — visto 20x, ruta mínima de 1 paso(s)."""
    page.goto(base_url)
    settle(page)
    require(page, 'a[href="/about"]:visible')
    page.locator('a[href="/about"]:visible').first.click()
    settle(page)
    monitor.scan_dom(page)
    monitor.assert_absent('http_404 GET /static/team.png')


@pytest.mark.formicidae
def test_bug_07_http_404_get_blog_old_post(page, monitor, base_url):
    """[sev 2] http_404 GET /blog/old-post — visto 9x, ruta mínima de 2 paso(s)."""
    page.goto(base_url)
    settle(page)
    require(page, 'a[href="/blog"]:visible')
    page.locator('a[href="/blog"]:visible').first.click()
    settle(page)
    require(page, 'a[href="/blog/old-post"]:visible')
    page.locator('a[href="/blog/old-post"]:visible').first.click()
    settle(page)
    monitor.scan_dom(page)
    monitor.assert_absent('http_404 GET /blog/old-post')


@pytest.mark.formicidae
def test_bug_08_broken_image_static_team_png(page, monitor, base_url):
    """[sev 1] broken_image /static/team.png — visto 19x, ruta mínima de 1 paso(s)."""
    page.goto(base_url)
    settle(page)
    require(page, 'a[href="/about"]:visible')
    page.locator('a[href="/about"]:visible').first.click()
    settle(page)
    monitor.scan_dom(page)
    monitor.assert_absent('broken_image /static/team.png')
