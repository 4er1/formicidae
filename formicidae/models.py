from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from urllib.parse import parse_qsl, urlsplit

_UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
ID_RE = re.compile(rf"/(\d+|{_UUID})(?=[/?#\"\]]|$)")


def route_of(url: str) -> str:
    """URL -> plantilla de ruta. /products/7?q=1 -> /products/{id}?q"""
    u = urlsplit(url)
    path = ID_RE.sub("/{id}", u.path).rstrip("/") or "/"
    keys = sorted({k for k, _ in parse_qsl(u.query, keep_blank_values=True)})
    return path + ("?" + "&".join(keys) if keys else "")


@dataclass(frozen=True)
class Finding:
    kind: str       # http_error | js_exception | console_error | request_failed | broken_image | error_text | slow_response
    severity: int   # 1 (bajo) .. 5 (crítico)
    signature: str  # identifica el bug de forma estable (deduplica y sirve para asertar en el test)
    url: str

    def to_dict(self) -> dict:
        return asdict(self)
