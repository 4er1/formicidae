"""Minimización de casos: quita pasos del camino mientras el bug siga reproduciéndose (delta debugging simple)."""
from __future__ import annotations

from playwright.sync_api import Error as PWError

from .actions import Action, settle
from .detectors import Monitor


def _needed(a: Action) -> list[str]:
    return [a.selector] + ([s for _, s, _ in a.fills] if a.kind == "form" else [])


def reproduces(browser, cfg, path: list[dict], signature: str) -> bool:
    ctx = browser.new_context()
    try:
        page = ctx.new_page()
        page.set_default_timeout(cfg.timeout_ms)
        mon = Monitor(page, cfg.base_url, cfg.ignore, cfg.slow_ms)
        page.goto(cfg.base_url, wait_until="load")
        settle(page)
        for d in path:
            a = Action.from_dict(d)
            if any(page.locator(s).count() == 0 for s in _needed(a)):
                return False  # el camino recortado ya no es ejecutable
            a.perform(page, cfg.timeout_ms)
        mon.scan_dom(page)
        return any(f.signature == signature for f in mon.found)
    except PWError:
        return False
    finally:
        ctx.close()


def minimize(browser, cfg, path: list[dict], signature: str) -> list[dict]:
    """Quita bloques contiguos de todos los tamaños (grandes primero) mientras el bug siga reproduciéndose.

    Quitar pasos sueltos no basta: un desvío (A -> B -> C -> A) solo sale como bloque. Con caminos de
    <= ~10 pasos el costo (O(n^2) replays) es aceptable. Resultado: mínimo local, no óptimo global.
    """
    path = list(path)
    for size in range(len(path), 0, -1):
        i = 0
        while i < len(path):
            cand = path[:i] + path[i + size:]
            if len(cand) < len(path) and reproduces(browser, cfg, cand, signature):
                path = cand
            else:
                i += 1
    return path
