from __future__ import annotations

import os
import random
import time
from collections import Counter

from playwright.sync_api import Error as PWError
from playwright.sync_api import sync_playwright

from .ant import Ant
from .config import Config
from .models import route_of
from .pheromone import PheromoneMap


class Colony:
    def __init__(self, cfg: Config, pheromone_file: str | None = None, metrics=None, log=print):
        self.cfg, self.pheromone_file, self.metrics, self.log = cfg, pheromone_file, metrics, log

    def run(self) -> dict:
        cfg = self.cfg
        rng = random.Random(cfg.seed)
        pmap = PheromoneMap(cfg)
        if self.pheromone_file and os.path.exists(self.pheromone_file):
            pmap.load(self.pheromone_file)
        records: dict[str, dict] = {}
        visits: Counter = Counter()
        seen: set = set()
        history: list[dict] = []
        total_steps = 0
        start_route = route_of(cfg.base_url)
        t0 = time.time()

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=not cfg.headed)
            probe = browser.new_page()
            try:  # falla rápido y claro si la URL no responde
                probe.goto(cfg.base_url, timeout=cfg.timeout_ms)
            except PWError as e:
                browser.close()
                raise ConnectionError(f"No pude abrir {cfg.base_url}: {str(e).splitlines()[0]}") from e
            probe.close()
            for it in range(1, cfg.iterations + 1):
                it_steps = it_hits = 0
                n_before = len(records)
                for n in range(cfg.ants):
                    ctx = browser.new_context()
                    page = ctx.new_page()
                    page.set_default_timeout(cfg.timeout_ms)
                    try:
                        steps = Ant(page, cfg, pmap, rng, seen).walk()
                    except PWError as e:
                        self.log(f"  ! hormiga {it}.{n} abortó: {str(e).splitlines()[0]}")
                        steps = []
                    finally:
                        ctx.close()
                    visits[start_route] += 1
                    for i, s in enumerate(steps):
                        if s.action.kind != "goto":
                            it_steps += 1
                            total_steps += 1
                            visits[s.to_state] += 1
                        if not s.findings:
                            continue
                        it_hits += 1
                        path = [st.action.to_dict() for st in steps[: i + 1]
                                if st.seg == s.seg and st.action.kind != "goto"]
                        new_sev, old_sev = 0, 0
                        for f in s.findings:
                            rec = records.get(f.signature)
                            if rec is None:
                                new_sev = max(new_sev, f.severity)
                                records[f.signature] = {**f.to_dict(), "count": 1, "first_iteration": it,
                                                        "route": s.to_state, "path": path}
                            else:
                                old_sev = max(old_sev, f.severity)
                                rec["count"] += 1
                                if len(path) < len(rec["path"]):
                                    rec["path"] = path
                        sev = max(new_sev, old_sev * cfg.repeat_factor)  # lo nuevo pesa; lo ya conocido casi no
                        for back, j in enumerate(range(i, -1, -1)):  # refuerza la ruta que llevó al bug
                            if steps[j].seg != s.seg or back > 4:
                                break
                            pmap.deposit(steps[j].edge, cfg.q * sev * cfg.gamma ** back)
                pmap.evaporate()
                discovered = seen | set(visits)
                snap = {
                    "iteration": it, "steps": total_steps, "routes_visited": len(visits),
                    "coverage": round(len(visits) / max(1, len(discovered)), 3),
                    "findings_unique": len(records), "pheromone_total": round(pmap.total(), 2),
                    "hit_ratio": round(it_hits / max(1, it_steps), 3),
                    "new_findings": len(records) - n_before,
                }
                history.append(snap)
                if self.metrics:
                    self.metrics.update(snap, records)
                self.log(f"  iter {it}/{cfg.iterations}: {snap['findings_unique']} hallazgos únicos, "
                         f"cobertura {snap['coverage']:.0%}, feromona {snap['pheromone_total']}")
            if cfg.minimize:
                from .generator import TESTABLE
                from .minimize import minimize

                todo = [r for r in records.values() if r["kind"] in TESTABLE and len(r["path"]) > 1]
                self.log(f"  minimizando {len(todo)} caminos por replay…")
                for r in todo:
                    r["raw_path_len"] = len(r["path"])
                    r["path"] = minimize(browser, cfg, r["path"], r["signature"])
            browser.close()

        if self.pheromone_file:
            pmap.save(self.pheromone_file)
        return self._result(pmap, records, visits, seen, history, total_steps, time.time() - t0)

    def _result(self, pmap, records, visits, seen, history, total_steps, secs) -> dict:
        cfg = self.cfg
        heat: Counter = Counter()
        edges: dict[tuple, dict] = {}
        for edge, dst in pmap.dest.items():
            tau = pmap.get(edge)
            heat[dst] += max(0.0, tau - cfg.tau0)
            e = edges.setdefault((edge[0], dst), {"src": edge[0], "dst": dst, "tau": 0.0, "visits": 0})
            e["tau"] = max(e["tau"], round(tau, 2))
            e["visits"] += pmap.visits.get(edge, 0)
        by_route = Counter(r["route"] for r in records.values())
        routes = {r: {"visits": visits.get(r, 0), "findings": by_route.get(r, 0), "heat": round(heat.get(r, 0.0), 2)}
                  for r in set(visits) | set(heat) | set(seen)}
        return {
            "base_url": cfg.base_url, "config": cfg.to_dict(), "duration_s": round(secs, 1),
            "total_steps": total_steps, "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "findings": sorted(records.values(), key=lambda r: (-r["severity"], -r["count"])),
            "routes": routes, "edges": list(edges.values()), "history": history,
        }
