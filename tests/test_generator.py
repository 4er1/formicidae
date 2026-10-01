from formicidae.generator import render_tests, case_name, write_tests
from formicidae.report import render

RESULT = {
    "base_url": "http://localhost:5000", "generated_at": "now", "duration_s": 1, "total_steps": 3,
    "config": {"seed": 1, "ants": 1, "iterations": 1, "tau0": 1.0}, "routes": {"/": {"visits": 1, "findings": 1, "heat": 1.0}},
    "edges": [], "history": [{"iteration": 1, "routes_visited": 1, "coverage": 1.0, "findings_unique": 2,
                              "pheromone_total": 1.0, "hit_ratio": 0.5, "new_findings": 2, "steps": 3}],
    "findings": [
        {"kind": "slow_response", "severity": 1, "signature": "slow_response GET /r", "url": "", "count": 1,
         "first_iteration": 1, "route": "/r", "path": []},
        {"kind": "http_error", "severity": 5, "signature": "http_500 POST /cart/add", "url": "", "count": 2,
         "first_iteration": 1, "route": "/cart/add", "path": [
             {"kind": "link", "selector": 'a[href="/products/3"]:visible', "label": "P", "fills": []},
             {"kind": "form", "selector": 'form[action="/cart/add"]', "label": "",
              "fills": [["fill", 'form[action="/cart/add"] >> [name="qty"]', "-1"]]}]},
    ],
}


def test_el_codigo_generado_es_python_valido_y_solo_incluye_hallazgos_testeables():
    code, names = render_tests(RESULT)
    compile(code, "<generated>", "exec")
    assert names == [case_name(1, "http_500 POST /cart/add")]  # slow_response se reporta pero no se testea
    assert "monitor.assert_absent('http_500 POST /cart/add')" in code
    assert "require(page, 'a[href=\"/products/3\"]:visible')" in code
    assert "'-1'" in code and "requestSubmit" in code


def test_write_tests_crea_conftest_y_tests(tmp_path):
    write_tests(RESULT, str(tmp_path))
    assert (tmp_path / "conftest.py").exists() and (tmp_path / "test_formicidae_bugs.py").exists()
    compile((tmp_path / "conftest.py").read_text(), "conftest", "exec")


def test_el_reporte_html_se_renderiza_y_escapa():
    html = render(RESULT)
    assert "http_500 POST /cart/add" in html and "<script" not in html
