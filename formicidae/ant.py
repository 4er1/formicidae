from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from playwright.sync_api import Error as PWError

from .actions import Action, settle
from .detectors import Monitor
from .models import route_of

EXTERNAL = "(externo)"

EXTRACT_JS = """() => {
  const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const links = [...document.querySelectorAll('a[href]')].filter(vis).map(a => ({
    href: a.getAttribute('href'), abs: a.href, target: a.target, text: a.innerText.trim().slice(0, 40)}));
  const buttons = [...document.querySelectorAll('button, input[type=button], [role=button]')]
    .filter(b => vis(b) && !b.closest('form') && !b.disabled)
    .map(b => ({id: b.id, tag: b.tagName.toLowerCase(), text: (b.innerText || b.value || '').trim().slice(0, 40)}));
  const skip = ['hidden', 'submit', 'button', 'file', 'image', 'reset', 'checkbox', 'radio'];
  const forms = [...document.querySelectorAll('form')].map((f, i) => ({f, i})).filter(({f}) => vis(f)).map(({f, i}) => ({
    index: i, action: f.getAttribute('action'),
    fields: [...f.querySelectorAll('input, textarea, select')].filter(x => x.name && !skip.includes(x.type)).map(x => ({
      name: x.name, type: x.tagName === 'SELECT' ? 'select' : (x.tagName === 'TEXTAREA' ? 'textarea' : (x.type || 'text')),
      options: x.tagName === 'SELECT' ? [...x.options].map(o => o.value) : []}))
  }));
  return {links, buttons, forms};
}"""


@dataclass
class Step:
    edge: tuple
    action: Action
    to_state: str
    findings: list
    seg: int  # segmento: se incrementa cada vez que la hormiga vuelve al inicio


class Ant:
    def __init__(self, page, cfg, pmap, rng, seen_routes: set):
        self.page, self.cfg, self.pmap, self.rng, self.seen = page, cfg, pmap, rng, seen_routes
        u = urlsplit(cfg.base_url)
        self.origin = f"{u.scheme}://{u.netloc}"
        self.monitor = Monitor(page, cfg.base_url, cfg.ignore, cfg.slow_ms)
        self.exclude = [re.compile(p) for p in cfg.exclude]

    # -- recorrido ---------------------------------------------------------
    def walk(self) -> list[Step]:
        steps: list[Step] = []
        seg = 0
        state = self._begin(steps, seg)
        for _ in range(self.cfg.max_steps):
            cands = self._candidates()
            if not cands:  # callejón sin salida: vuelve al hormiguero
                seg += 1
                state = self._begin(steps, seg)
                continue
            act = self.pmap.choose(state, cands, self.rng)
            if act.kind == "form":
                act = act.fuzz(self.rng, self.pmap.tried)
            edge = self.pmap.visit(state, act)
            before = self.page.url
            try:
                act.perform(self.page, self.cfg.timeout_ms)
            except PWError:
                seg += 1
                state = self._begin(steps, seg)
                continue
            found = self.monitor.drain()
            if self.page.url != before or act.kind == "form":
                found += self.monitor.scan_dom(self.page)
            external = not self.page.url.startswith(self.origin)
            to = EXTERNAL if external else route_of(self.page.url)
            self.pmap.dest[edge] = to
            steps.append(Step(edge, act, to, found, seg))
            if external:
                seg += 1
                state = self._begin(steps, seg)
            else:
                state = to
        return steps

    def _begin(self, steps: list, seg: int) -> str:
        self.page.goto(self.cfg.base_url, wait_until="load")
        settle(self.page)
        found = self.monitor.drain() + self.monitor.scan_dom(self.page)
        to = route_of(self.page.url)
        if found:
            steps.append(Step(("(inicio)", "goto:/"), Action("goto", self.cfg.base_url), to, found, seg))
        return to

    # -- percepción --------------------------------------------------------
    def _ok(self, url: str) -> bool:
        return url.startswith(self.origin) and not any(rx.search(url) for rx in self.exclude)

    def _candidates(self) -> list[Action]:
        try:
            data = self.page.evaluate(EXTRACT_JS)
        except PWError:
            return []
        acts, seen_href = [], set()
        for l in data["links"]:
            href = l["href"]
            if href.startswith(("#", "javascript:", "mailto:", "tel:")) or l["target"] == "_blank":
                continue
            if not self._ok(l["abs"]):
                continue
            self.seen.add(route_of(l["abs"]))
            if href not in seen_href:
                seen_href.add(href)
                acts.append(Action("link", f'a[href="{href}"]:visible', l["text"]))
        for b in data["buttons"]:
            if b["id"]:
                acts.append(Action("button", f'#{b["id"]}', b["text"]))
            elif b["text"] and '"' not in b["text"]:
                acts.append(Action("button", f'{b["tag"]}:has-text("{b["text"]}"):visible', b["text"]))
        for f in data["forms"]:
            sel = f'form[action="{f["action"]}"]' if f["action"] else f'form >> nth={f["index"]}'
            if f["fields"]:
                acts.append(Action("form", sel, "", fields=f["fields"]))
        return acts
