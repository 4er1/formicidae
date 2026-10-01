from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Config:
    base_url: str
    ants: int = 5            # hormigas por iteración
    iterations: int = 6      # iteraciones de la colonia (evaporación al final de cada una)
    max_steps: int = 10      # pasos máximos por hormiga
    alpha: float = 1.0       # peso de la feromona
    beta: float = 1.5        # peso de la novedad (heurística 1/(1+visitas))
    rho: float = 0.15        # tasa de evaporación
    q: float = 2.0           # depósito base: q * severidad
    gamma: float = 0.6       # decaimiento del depósito hacia atrás en la ruta
    repeat_factor: float = 0.1  # un hallazgo ya conocido deposita solo esta fracción (evita estancarse)
    tau0: float = 1.0        # feromona inicial de toda arista
    tau_min: float = 0.1
    tau_max: float = 50.0
    seed: int | None = None
    minimize: bool = True    # reduce cada camino al mínimo que aún reproduce el bug
    headed: bool = False
    slow_ms: int = 3000
    timeout_ms: int = 8000
    ignore: tuple = (r"/favicon\.ico",)  # regex de hallazgos a ignorar
    exclude: tuple = ()                  # regex de URLs que las hormigas NO deben seguir (p. ej. logout)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ignore"], d["exclude"] = list(self.ignore), list(self.exclude)
        return d
