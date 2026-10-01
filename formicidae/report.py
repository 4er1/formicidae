"""Reporte HTML autocontenido: mapa de feromonas, convergencia, rutas calientes y hallazgos."""
from __future__ import annotations

from html import escape

from jinja2 import Environment
from markupsafe import Markup

from .actions import Action
from .generator import case_name, testable_sorted

W, ROW = 920, 100


def _heat_color(t: float) -> str:
    return f"hsl({175 * (1 - min(1.0, max(0.0, t))):.0f},75%,52%)"


def _graph(res: dict) -> Markup:
    routes, edges = res["routes"], res["edges"]
    if not routes:
        return Markup("")
    adj: dict[str, set] = {}
    for e in edges:
        adj.setdefault(e["src"], set()).add(e["dst"])
    root = "/" if "/" in routes else next(iter(routes))
    layer, queue = {root: 0}, [root]
    while queue:
        n = queue.pop(0)
        for m in sorted(adj.get(n, ())):
            if m not in layer:
                layer[m] = layer[n] + 1
                queue.append(m)
    last = max(layer.values())
    for r in routes:
        layer.setdefault(r, last + 1)
    by_layer: dict[int, list] = {}
    for r, l in layer.items():
        by_layer.setdefault(l, []).append(r)
    pos = {}
    for l, names in by_layer.items():
        names.sort(key=lambda r: -routes.get(r, {}).get("heat", 0))
        for i, r in enumerate(names):
            pos[r] = ((i + 1) * W / (len(names) + 1), 50 + l * ROW)
    H = 80 + (max(by_layer) + 1) * ROW - 30
    maxheat = max((v["heat"] for v in routes.values()), default=0) or 1
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Mapa de feromonas" style="width:100%;height:auto">']
    tau0 = res["config"]["tau0"]
    for hot in (False, True):
        for e in edges:
            if e["src"] == e["dst"] or e["src"] not in pos or e["dst"] not in pos or (e["tau"] > tau0) != hot:
                continue
            (x1, y1), (x2, y2) = pos[e["src"]], pos[e["dst"]]
            cx, cy = (x1 + x2) / 2 + (y2 - y1) * 0.12, (y1 + y2) / 2 - (x2 - x1) * 0.12
            w = 0.6 + min(e["tau"], 25) / 6
            col, op = ("#ff6b4a", 0.8) if hot else ("var(--mut)", 0.28)
            out.append(f'<path d="M{x1:.0f} {y1:.0f} Q{cx:.0f} {cy:.0f} {x2:.0f} {y2:.0f}" fill="none" '
                       f'stroke="{col}" stroke-width="{w:.1f}" opacity="{op}"/>')
    for r, (x, y) in pos.items():
        v = routes.get(r, {"visits": 0, "findings": 0, "heat": 0})
        t = 0.55 * v["heat"] / maxheat + 0.45 * min(v["findings"], 2) / 2
        rad = 9 + min(v["visits"], 60) ** 0.5 * 1.6
        out.append(f'<g><title>{escape(r)} · visitas {v["visits"]} · hallazgos {v["findings"]} · calor {v["heat"]}</title>'
                   f'<circle cx="{x:.0f}" cy="{y}" r="{rad:.1f}" fill="{_heat_color(t)}" stroke="var(--bg)" stroke-width="2"/>'
                   f'<text x="{x:.0f}" y="{y + rad + 14:.0f}" text-anchor="middle" font-size="11" fill="var(--fg)">{escape(r)}</text></g>')
    out.append("</svg>")
    return Markup("".join(out))


def _spark(values: list, w: int = 230, h: int = 52, fmt: str = "{:g}") -> Markup:
    if not values:
        return Markup("")
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    pts = " ".join(f"{4 + i * (w - 8) / max(1, len(values) - 1):.1f},{h - 6 - (v - lo) / span * (h - 14):.1f}"
                   for i, v in enumerate(values))
    return Markup(f'<svg viewBox="0 0 {w} {h}" style="width:100%;height:auto"><polyline points="{pts}" fill="none" '
                  f'stroke="var(--ok)" stroke-width="2.2" stroke-linejoin="round"/></svg>'
                  f'<div class="mut">inicio {fmt.format(values[0])} → final {fmt.format(values[-1])}</div>')


TEMPLATE = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Formicidae · {{ r.base_url }}</title>
<style>
:root{--bg:#0e1116;--card:#161b22;--fg:#e6edf3;--mut:#8b949e;--line:#2a313c;--hot:#ff6b4a;--ok:#2dd4bf}
@media (prefers-color-scheme:light){:root{--bg:#f6f8fa;--card:#fff;--fg:#1f2328;--mut:#59636e;--line:#d0d7de;--ok:#0f9d8a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1000px;margin:0 auto;padding:28px 18px 60px}h1{font-size:26px;margin:0}h2{font-size:17px;margin:34px 0 12px}
.mut{color:var(--mut);font-size:13px}.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.kpi b{display:block;font-size:26px;line-height:1.1}table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top;font-size:14px}th{color:var(--mut);font-weight:600;font-size:12px}
.wrap{overflow-x:auto}code{font:12.5px ui-monospace,Menlo,Consolas,monospace;word-break:break-all}
.sev{display:inline-block;min-width:26px;text-align:center;border-radius:6px;padding:1px 7px;font-weight:700;font-size:12px;color:#fff}
.s5{background:#d1242f}.s4{background:#e16f24}.s3{background:#bf8700}.s2{background:#3b82c4}.s1{background:#6e7781}
.bar{height:8px;border-radius:4px;background:var(--line);overflow:hidden;min-width:70px}.bar i{display:block;height:100%}
ol{margin:4px 0 0;padding-left:20px}details summary{cursor:pointer;color:var(--mut);font-size:13px}
</style></head><body><main>
<h1>🐜 Formicidae</h1>
<div class="mut">{{ r.base_url }} · {{ r.generated_at }} · {{ r.duration_s }}s · semilla {{ r.config.seed if r.config.seed is not none else 'aleatoria' }}</div>
<h2>Resumen</h2><div class="grid">
<div class="card kpi"><b>{{ r.findings|length }}</b><span class="mut">hallazgos únicos</span></div>
<div class="card kpi"><b>{{ maxsev }}</b><span class="mut">severidad máxima (1–5)</span></div>
<div class="card kpi"><b>{{ last.routes_visited }}</b><span class="mut">rutas visitadas</span></div>
<div class="card kpi"><b>{{ (last.coverage*100)|round|int }}%</b><span class="mut">cobertura de rutas</span></div>
<div class="card kpi"><b>{{ r.total_steps }}</b><span class="mut">pasos · {{ r.config.ants }}🐜 × {{ r.config.iterations }} it.</span></div></div>
<h2>Mapa de feromonas</h2><div class="card">{{ graph }}
<div class="mut">Color: frío → caliente según feromona acumulada y hallazgos · tamaño: visitas · trazos naranjas: aristas reforzadas por la colonia.</div></div>
<h2>Convergencia de la colonia</h2><div class="grid">
<div class="card"><b>Hallazgos únicos (acum.)</b>{{ sp_find }}</div>
<div class="card"><b>Cobertura de rutas</b>{{ sp_cov }}</div>
<div class="card"><b>Feromona total</b>{{ sp_tau }}</div>
</div>
<h2>Rutas por calor</h2><div class="card wrap"><table><tr><th>Ruta</th><th>Calor</th><th>Visitas</th><th>Hallazgos</th></tr>
{% for name, v in routes %}<tr><td><code>{{ name }}</code></td>
<td><div class="bar"><i style="width:{{ (v.heat/maxheat*100)|round|int }}%;background:{{ v.color }}"></i></div></td>
<td>{{ v.visits }}</td><td>{{ v.findings or '' }}</td></tr>{% endfor %}</table></div>
<h2>Hallazgos</h2><div class="card wrap"><table><tr><th>Sev</th><th>Hallazgo</th><th>Veces</th><th>Camino mínimo</th></tr>
{% for f in findings %}<tr><td><span class="sev s{{ f.severity }}">{{ f.severity }}</span></td>
<td><code>{{ f.signature }}</code><div class="mut">{{ f.kind }} · iteración {{ f.first_iteration }}{% if f.test %} · <code>{{ f.test }}</code>{% endif %}</div></td>
<td>{{ f.count }}</td><td>{% if f.steps %}<details><summary>{{ f.steps|length }} paso(s){% if f.raw_path_len and f.raw_path_len != f.steps|length %} (de {{ f.raw_path_len }}){% endif %}</summary>
<ol>{% for s in f.steps %}<li><code>{{ s }}</code></li>{% endfor %}</ol></details>{% else %}<span class="mut">página de inicio</span>{% endif %}</td></tr>{% endfor %}</table></div>
</main></body></html>"""


def render(res: dict) -> str:
    hist = res["history"] or [{"routes_visited": 0, "coverage": 0}]
    maxheat = max((v["heat"] for v in res["routes"].values()), default=0) or 1
    routes = sorted(res["routes"].items(), key=lambda kv: (-kv[1]["heat"], -kv[1]["visits"]))
    routes = [(n, {**v, "color": _heat_color(0.55 * v["heat"] / maxheat + 0.45 * min(v["findings"], 2) / 2)}) for n, v in routes]
    names = {r["signature"]: case_name(i, r["signature"]) for i, r in enumerate(testable_sorted(res), 1)}
    findings = [{**f, "test": names.get(f["signature"]), "steps": [Action.from_dict(a).describe() for a in f["path"]]}
                for f in res["findings"]]
    return Environment(autoescape=True).from_string(TEMPLATE).render(
        r=res, last=hist[-1], maxheat=maxheat, routes=routes, findings=findings,
        maxsev=max((f["severity"] for f in res["findings"]), default=0), graph=_graph(res),
        sp_find=_spark([h["findings_unique"] for h in hist]),
        sp_cov=_spark([h["coverage"] * 100 for h in hist], fmt="{:.0f}%"),
        sp_tau=_spark([h["pheromone_total"] for h in hist], fmt="{:.0f}"))
