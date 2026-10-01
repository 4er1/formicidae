import random

from formicidae.actions import PAYLOADS, Action
from formicidae.config import Config
from formicidae.models import route_of
from formicidae.pheromone import PheromoneMap


def test_route_of_generaliza_ids_y_query():
    assert route_of("http://x/products/7/reviews") == "/products/{id}/reviews"
    assert route_of("http://x/search?q=a&z=1") == "/search?q&z"
    assert route_of("http://x/") == "/"
    assert route_of("http://x/u/123e4567-e89b-12d3-a456-426614174000") == "/u/{id}"


def test_key_del_link_generaliza_ids():
    a = Action("link", 'a[href="/products/7/reviews"]:visible')
    assert a.key == 'link:a[href="/products/{id}/reviews"]:visible'
    assert a.ident != a.key  # la novedad sí distingue la instancia exacta


def test_evaporacion_respeta_el_piso():
    cfg = Config("http://x", rho=0.5, tau_min=0.3)
    pm = PheromoneMap(cfg)
    pm.deposit(("/", "k"), 4.0)  # 1.0 + 4.0
    pm.evaporate()
    assert pm.get(("/", "k")) == 2.5
    for _ in range(10):
        pm.evaporate()
    assert pm.get(("/", "k")) == 0.3


def test_deposito_tiene_tope():
    pm = PheromoneMap(Config("http://x", tau_max=10))
    pm.deposit(("/", "k"), 999)
    assert pm.get(("/", "k")) == 10


def test_choose_prefiere_la_arista_con_feromona():
    pm = PheromoneMap(Config("http://x", beta=0))  # sin novedad: solo feromona
    a, b = Action("link", 'a[href="/a"]'), Action("link", 'a[href="/b"]')
    pm.deposit(("/", a.key), 20)
    rng = random.Random(1)
    picks = [pm.choose("/", [a, b], rng).selector for _ in range(500)]
    assert picks.count('a[href="/a"]') > 400


def test_novedad_de_links_es_global():
    pm = PheromoneMap(Config("http://x"))
    about = Action("link", 'a[href="/about"]')
    other = Action("link", 'a[href="/other"]')
    pm.visit("/", about)
    assert pm.weight("/faq", about) < pm.weight("/faq", other)  # visitado desde "/" => menos atractivo en cualquier página


def test_fuzz_prueba_todos_los_payloads_antes_de_repetir():
    act = Action("form", 'form[action="/x"]', fields=[{"name": "q", "type": "search", "options": []}])
    rng, tried = random.Random(3), {}
    vals = {act.fuzz(rng, tried).fills[0][2] for _ in range(len(PAYLOADS["text"]))}
    assert vals == set(PAYLOADS["text"])


def test_guardar_y_cargar_feromona(tmp_path):
    cfg = Config("http://x")
    pm = PheromoneMap(cfg)
    pm.deposit(("/p", "link:a"), 5)
    pm.dest[("/p", "link:a")] = "/q"
    pm.save(tmp_path / "ph.json")
    pm2 = PheromoneMap(cfg)
    pm2.load(tmp_path / "ph.json")
    assert pm2.get(("/p", "link:a")) == 6 and pm2.dest[("/p", "link:a")] == "/q"
