"""Bucle completo: colonia -> hallazgos -> tests generados -> fallan con el bug / pasan con el bug corregido."""
import os
import pathlib
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

from formicidae.colony import Colony
from formicidae.config import Config
from formicidae.generator import write_tests

pytestmark = pytest.mark.e2e
ROOT = pathlib.Path(__file__).resolve().parents[1]

EXPECTED = {
    "http_500 GET /products/7/reviews", "http_500 GET /search", "http_500 POST /cart/add",
    "js_exception ReferenceError: sendMessage is not defined", "console_error Config de FAQ no cargada",
    "http_404 GET /static/team.png", "http_404 GET /blog/old-post", "broken_image /static/team.png",
}


def _serve(fixed: bool):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    proc = subprocess.Popen([sys.executable, "-m", "demo_app.app", "--port", str(port)], cwd=ROOT,
                            env={**os.environ, "DEMO_FIXED": "1" if fixed else "0"},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(url, timeout=1)
            return proc, url
        except Exception:
            time.sleep(0.2)
    proc.kill()
    raise RuntimeError("la app demo no arrancó")


def _run_pytest(tests_dir, url):
    return subprocess.run([sys.executable, "-m", "pytest", str(tests_dir), "-q", "-p", "no:cacheprovider"],
                          cwd=tests_dir, capture_output=True, text=True,
                          env={**os.environ, "FORMICIDAE_BASE_URL": url, "PYTHONPATH": str(ROOT)})


def test_la_colonia_encuentra_los_bugs_y_los_tests_generados_los_reproducen(tmp_path):
    proc, url = _serve(fixed=False)
    try:
        res = Colony(Config(url, seed=42), log=lambda *_: None).run()
        found = {f["signature"] for f in res["findings"]}
        assert EXPECTED <= found, f"faltan: {EXPECTED - found}"
        names = write_tests(res, str(tmp_path))
        assert len(names) == len(EXPECTED)
        buggy = _run_pytest(tmp_path, url)
    finally:
        proc.kill()
    assert buggy.returncode == 1 and "passed" not in buggy.stdout, buggy.stdout[-800:]

    proc, url = _serve(fixed=True)  # misma suite contra la app corregida
    try:
        fixed = _run_pytest(tmp_path, url)
    finally:
        proc.kill()
    assert fixed.returncode == 0 and "failed" not in fixed.stdout, fixed.stdout[-800:]
