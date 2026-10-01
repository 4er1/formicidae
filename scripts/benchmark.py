"""Colonia (ACO) vs recorrido aleatorio con el MISMO presupuesto de pasos, sobre la app demo.

El baseline aleatorio usa alpha=0, beta=0 (elección uniforme) pero conserva la rotación de payloads en formularios,
así que es una referencia conservadora (más fuerte que un fuzzer puramente aleatorio).

    python scripts/benchmark.py --seeds 5 --workers 4
"""
import argparse
import os
import pathlib
import socket
import statistics
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ProcessPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
STRATEGIES = {"colonia": dict(alpha=1.0, beta=1.5), "aleatorio": dict(alpha=0.0, beta=0.0)}


def _serve():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    proc = subprocess.Popen([sys.executable, "-m", "demo_app.app", "--port", str(port)], cwd=ROOT,
                            env={**os.environ, "DEMO_SLOW_SECONDS": "1.2"},  # endpoint lento más corto: benchmark más rápido
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(url, timeout=1)
            return proc, url
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("la app demo no arrancó")


def job(args):
    name, seed, ants, iters, steps = args
    from formicidae.colony import Colony
    from formicidae.config import Config

    proc, url = _serve()
    try:
        cfg = Config(url, seed=seed, ants=ants, iterations=iters, max_steps=steps, minimize=False, slow_ms=1000, **STRATEGIES[name])
        res = Colony(cfg, log=lambda *_: None).run()
        return name, seed, [h["findings_unique"] for h in res["history"]], res["history"][-1]["coverage"]
    finally:
        proc.kill()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--ants", type=int, default=5)
    ap.add_argument("--iterations", type=int, default=6)
    ap.add_argument("--steps", type=int, default=10)
    a = ap.parse_args()
    jobs = [(n, s, a.ants, a.iterations, a.steps) for s in range(1, a.seeds + 1) for n in STRATEGIES]
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        results = list(ex.map(job, jobs))
    print(f"\nHallazgos únicos acumulados por iteración ({a.seeds} semillas, {a.ants}🐜 × {a.steps} pasos por iteración)\n")
    print("| iteración | " + " | ".join(STRATEGIES) + " |\n|---|" + "---|" * len(STRATEGIES))
    for i in range(a.iterations):
        row = [statistics.mean(r[2][i] for r in results if r[0] == n) for n in STRATEGIES]
        print(f"| {i + 1} | " + " | ".join(f"{v:.1f}" for v in row) + " |")
    print()
    for n in STRATEGIES:
        finals = [r[2][-1] for r in results if r[0] == n]
        cov = statistics.mean(r[3] for r in results if r[0] == n)
        print(f"- {n}: final {statistics.mean(finals):.1f} (mín {min(finals)}, máx {max(finals)}), cobertura media {cov:.0%}, por semilla {finals}")


if __name__ == "__main__":
    main()
