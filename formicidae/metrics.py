from __future__ import annotations


class Metrics:
    """Expone métricas de la colonia para Prometheus (requiere `pip install formicidae[metrics]`)."""

    def __init__(self, port: int):
        from prometheus_client import Gauge, start_http_server

        self._g = {
            "steps": Gauge("formicidae_steps", "Pasos totales ejecutados por la colonia"),
            "routes_visited": Gauge("formicidae_routes_visited", "Rutas (plantillas) visitadas"),
            "coverage": Gauge("formicidae_route_coverage_ratio", "Rutas visitadas / rutas descubiertas"),
            "findings_unique": Gauge("formicidae_findings_unique", "Hallazgos únicos"),
            "pheromone_total": Gauge("formicidae_pheromone_total", "Feromona total en el mapa"),
            "hit_ratio": Gauge("formicidae_hit_ratio", "Pasos con hallazgo / pasos de la iteración"),
        }
        self._sev = Gauge("formicidae_findings_by_severity", "Hallazgos únicos por severidad", ["severity"])
        start_http_server(port)

    def update(self, snap: dict, records: dict) -> None:
        for k, g in self._g.items():
            g.set(snap["routes_visited"] if k == "routes_visited" else snap[k])
        for sev in range(1, 6):
            self._sev.labels(str(sev)).set(sum(1 for r in records.values() if r["severity"] == sev))
