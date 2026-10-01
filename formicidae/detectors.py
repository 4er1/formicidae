from __future__ import annotations

import re
from urllib.parse import urlsplit

from .models import Finding

ERROR_TEXT = re.compile(
    r"Traceback \(most recent call last\)|Unhandled (?:Exception|Rejection)|Fatal error|Whitelabel Error|Warning: .{0,60} on line \d+"
)
DOM_JS = """() => ({
  broken: [...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.getAttribute('src')).map(i => i.getAttribute('src')),
  text: document.body ? document.body.innerText.slice(0, 5000) : ""
})"""


class Monitor:
    """Se engancha a una Page de Playwright y convierte eventos en Findings."""

    def __init__(self, page, base_url: str, ignore=(r"/favicon\.ico",), slow_ms: int = 3000):
        u = urlsplit(base_url)
        self.origin = f"{u.scheme}://{u.netloc}"
        self.ignore = [re.compile(p) for p in ignore]
        self.slow_ms = slow_ms
        self.found: list[Finding] = []
        self._cursor = 0
        page.on("response", self._response)
        page.on("pageerror", self._pageerror)
        page.on("console", self._console)
        page.on("requestfailed", self._failed)
        page.on("requestfinished", self._finished)

    # -- API -------------------------------------------------------------
    def drain(self) -> list[Finding]:
        new = self.found[self._cursor:]
        self._cursor = len(self.found)
        return new

    def scan_dom(self, page) -> list[Finding]:
        try:
            d = page.evaluate(DOM_JS)
        except Exception:
            return []
        for src in d["broken"]:
            if not src.startswith("data:"):
                self._add("broken_image", 1, f"broken_image {src}", page.url)
        m = ERROR_TEXT.search(d["text"])
        if m:
            self._add("error_text", 3, f"error_text {m.group(0)[:60]}", page.url)
        new = self.found[self._cursor:]
        self._cursor = len(self.found)
        return new

    def assert_absent(self, signature: str) -> None:
        hits = [f for f in self.found if f.signature == signature]
        assert not hits, f"Formicidae reprodujo el bug: {signature} (en {hits[0].url})"

    # -- internos --------------------------------------------------------
    def _same(self, url: str) -> bool:
        return url.startswith(self.origin)

    def _add(self, kind: str, severity: int, signature: str, url: str) -> None:
        if any(rx.search(signature) or rx.search(url) for rx in self.ignore):
            return
        self.found.append(Finding(kind, severity, signature, url))

    def _response(self, r) -> None:
        if r.status < 400 or not self._same(r.url):
            return
        sev = 5 if r.status >= 500 else 2 if r.status == 404 else 1
        sig = f"http_{r.status} {r.request.method} {urlsplit(r.url).path}"
        self._add("http_error", sev, sig, r.url)

    def _pageerror(self, err) -> None:
        name = getattr(err, "name", "Error")
        msg = getattr(err, "message", str(err))
        self._add("js_exception", 4, f"js_exception {name}: {msg}"[:140], "")

    def _console(self, msg) -> None:
        # los "Failed to load resource" ya los cubre el evento response
        if msg.type == "error" and not msg.text.startswith("Failed to load resource"):
            self._add("console_error", 2, f"console_error {msg.text}"[:140], msg.location.get("url", ""))

    def _failed(self, req) -> None:
        err = req.failure or ""
        if "ERR_ABORTED" not in err and self._same(req.url):
            self._add("request_failed", 2, f"request_failed {req.method} {urlsplit(req.url).path}", req.url)

    def _finished(self, req) -> None:
        if req.resource_type != "document" or not self._same(req.url):
            return
        try:
            ms = req.timing.get("responseEnd", -1)
        except Exception:
            return
        if ms > self.slow_ms:
            self._add("slow_response", 1, f"slow_response {req.method} {urlsplit(req.url).path}", req.url)
