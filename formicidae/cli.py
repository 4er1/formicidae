from __future__ import annotations

import argparse
import json
import os
import time

from .config import Config
from .generator import write_tests


def _summary(res: dict, names: list[str], out: str) -> None:
    print(f"\n🐜 {len(res['findings'])} hallazgos únicos · {res['total_steps']} pasos · {res['duration_s']}s")
    for f in res["findings"]:
        print(f"  [sev {f['severity']}] {f['signature']}  (x{f['count']})")
    print(f"\n  reporte : {os.path.join(out, 'report.html')}\n  json    : {os.path.join(out, 'result.json')}\n"
          f"  tests   : {os.path.join(out, 'generated_tests')} ({len(names)} generados)")


def _cmd_run(a) -> int:
    from .colony import Colony
    from .report import render

    cfg = Config(a.url, ants=a.ants, iterations=a.iterations, max_steps=a.steps, seed=a.seed,
                 headed=a.headed, minimize=not a.no_minimize, exclude=tuple(a.exclude), ignore=Config.ignore + tuple(a.ignore))
    metrics = None
    if a.metrics_port:
        from .metrics import Metrics
        metrics = Metrics(a.metrics_port)
        print(f"métricas Prometheus en http://localhost:{a.metrics_port}/metrics")
    print(f"🐜 Colonia lista: {cfg.ants} hormigas × {cfg.iterations} iteraciones × {cfg.max_steps} pasos → {cfg.base_url}")
    try:
        res = Colony(cfg, pheromone_file=a.pheromones, metrics=metrics).run()
    except ConnectionError as e:
        print(f"✗ {e}")
        return 2
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "result.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    with open(os.path.join(a.out, "report.html"), "w", encoding="utf-8") as f:
        f.write(render(res))
    names = write_tests(res, os.path.join(a.out, "generated_tests"))
    _summary(res, names, a.out)
    if metrics and a.metrics_linger:
        print(f"manteniendo /metrics {a.metrics_linger}s para que Prometheus haga scrape…")
        time.sleep(a.metrics_linger)
    if a.fail_on and any(f["severity"] >= a.fail_on for f in res["findings"]):
        return 1
    return 0


def _cmd_report(a) -> int:
    from .report import render

    with open(a.result, encoding="utf-8") as f:
        res = json.load(f)
    out = a.output or os.path.join(os.path.dirname(a.result) or ".", "report.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(res))
    print(out)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="formicidae", description="Exploratory testing con colonia de hormigas")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="lanza la colonia contra una URL")
    r.add_argument("url")
    r.add_argument("--ants", type=int, default=5)
    r.add_argument("--iterations", type=int, default=6)
    r.add_argument("--steps", type=int, default=10, help="pasos máximos por hormiga")
    r.add_argument("--seed", type=int, default=None)
    r.add_argument("--out", default="formicidae-out")
    r.add_argument("--exclude", action="append", default=[], help="regex de URLs a NO seguir (p. ej. logout)")
    r.add_argument("--ignore", action="append", default=[], help="regex de hallazgos a ignorar")
    r.add_argument("--pheromones", help="archivo JSON para persistir la feromona entre ejecuciones")
    r.add_argument("--fail-on", type=int, metavar="SEV", help="exit 1 si hay hallazgos con severidad >= SEV")
    r.add_argument("--headed", action="store_true")
    r.add_argument("--no-minimize", action="store_true", help="no reducir los caminos por replay")
    r.add_argument("--metrics-port", type=int)
    r.add_argument("--metrics-linger", type=int, default=30)
    r.set_defaults(fn=_cmd_run)
    g = sub.add_parser("report", help="regenera el HTML desde result.json")
    g.add_argument("result")
    g.add_argument("-o", "--output")
    g.set_defaults(fn=_cmd_report)
    a = ap.parse_args(argv)
    return a.fn(a)
