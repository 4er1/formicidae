from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import ID_RE

SETTLE_MS = 250


def settle(page) -> None:
    """Espera carga + un respiro para que aparezcan errores JS / peticiones tardías."""
    page.wait_for_load_state("load")
    page.wait_for_timeout(SETTLE_MS)


def require(page, selector: str) -> None:
    """Si el elemento ya no existe, el camino quedó obsoleto (¿bug corregido o UI cambiada?): skip explícito."""
    if page.locator(selector).count() == 0:
        import pytest

        pytest.skip(f"camino obsoleto: ya no existe {selector}")


PAYLOADS = {
    "text": ["hello", "", "' OR '1'='1", "<script>alert(1)</script>", "a" * 300, "O'Brien",
             "%s%s%s", "../../etc/passwd", "😀", "null"],
    "email": ["test@example.com", "not-an-email", "", "a@b", "x" * 200 + "@x.com"],
    "password": ["secret123", "", "' OR 1=1 --"],
    "number": ["1", "0", "-1", "999999999", "2"],
    "tel": ["999888777", "", "+51 999"],
    "url": ["https://example.com", "javascript:alert(1)", ""],
    "date": ["2026-01-01", "1900-01-01"],
}
PAYLOADS["search"] = PAYLOADS["textarea"] = PAYLOADS["text"]


@dataclass
class Action:
    kind: str                 # link | button | form | goto
    selector: str
    label: str = ""
    fills: list = field(default_factory=list)            # [[op, selector, valor]] (solo forms)
    fields: list = field(default_factory=list, repr=False, compare=False)  # metadatos para fuzzing

    @property
    def key(self) -> str:
        """Clave de la arista. En links los ids se generalizan (/products/{id}/reviews)."""
        sel = ID_RE.sub("/{id}", self.selector) if self.kind == "link" else self.selector
        return f"{self.kind}:{sel}"

    @property
    def ident(self) -> str:
        return f"{self.kind}:{self.selector}"

    def fuzz(self, rng, tried: dict | None = None) -> "Action":
        """Rellena el formulario; prefiere payloads que aún no se han probado en ese campo."""
        tried = tried if tried is not None else {}
        fills = []
        for f in self.fields:
            sel = f'{self.selector} >> [name="{f["name"]}"]'
            pool = f["options"] if f["type"] == "select" else PAYLOADS.get(f["type"], PAYLOADS["text"])
            if not pool:
                continue
            used = tried.setdefault(f"{sel}", set())
            fresh = [v for v in pool if v not in used] or pool
            val = rng.choice(fresh)
            used.add(val)
            fills.append(["select" if f["type"] == "select" else "fill", sel, val])
        return Action("form", self.selector, self.label, fills)

    def perform(self, page, timeout: int = 8000) -> None:
        if self.kind in ("link", "button"):
            page.locator(self.selector).first.click(timeout=timeout)
        elif self.kind == "form":
            for op, sel, val in self.fills:
                loc = page.locator(sel).first
                loc.fill(val, timeout=timeout) if op == "fill" else loc.select_option(val, timeout=timeout)
            page.locator(self.selector).first.evaluate("f => f.requestSubmit()")
        settle(page)

    def to_code(self) -> list[str]:
        """Las mismas acciones que perform(), como líneas de Playwright para el test."""
        if self.kind in ("link", "button"):
            lines = [f"require(page, {self.selector!r})", f"page.locator({self.selector!r}).first.click()"]
        else:
            lines = [f"require(page, {self.selector!r})"]
            for op, sel, val in self.fills:
                meth = "fill" if op == "fill" else "select_option"
                lines += [f"require(page, {sel!r})", f"page.locator({sel!r}).first.{meth}({val!r})"]
            lines.append(f"page.locator({self.selector!r}).first.evaluate(\"f => f.requestSubmit()\")")
        return lines + ["settle(page)"]

    def describe(self) -> str:
        if self.kind == "form":
            vals = []
            for _, sel, val in self.fills:
                m = re.search(r'\[name="([^"]+)"\]', sel)
                vals.append(f"{m.group(1) if m else '?'}={val[:24]!r}")
            return f"form {self.selector} ← " + ", ".join(vals)
        return f"{self.kind} {self.label or self.selector}".strip()

    def to_dict(self) -> dict:
        return {"kind": self.kind, "selector": self.selector, "label": self.label, "fills": self.fills}

    @staticmethod
    def from_dict(d: dict) -> "Action":
        return Action(d["kind"], d["selector"], d.get("label", ""), d.get("fills", []))
