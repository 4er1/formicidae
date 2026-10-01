from __future__ import annotations

import json
import random

from .config import Config

SEP = "\t"


class PheromoneMap:
    """Feromona sobre aristas (estado, acción). Estado = plantilla de ruta."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.tau: dict[tuple, float] = {}
        self.visits: dict[tuple, int] = {}
        self.dest: dict[tuple, str] = {}  # arista -> estado destino (para el grafo)
        self.inst: dict[tuple, int] = {}  # visitas por instancia concreta (/products/3 != /products/7)
        self.tried: dict[str, set] = {}   # payloads ya probados por campo de formulario

    def get(self, edge: tuple) -> float:
        return self.tau.get(edge, self.cfg.tau0)

    def weight(self, state: str, action) -> float:
        # tau generaliza por plantilla (/products/{id}/reviews); eta mide novedad de la instancia exacta
        eta = 1.0 / (1 + self.inst.get(self._ikey(state, action), 0))
        return (self.get((state, action.key)) ** self.cfg.alpha) * (eta ** self.cfg.beta)

    def choose(self, state: str, actions: list, rng: random.Random):
        weights = [self.weight(state, a) for a in actions]
        return rng.choices(actions, weights=weights)[0]

    def visit(self, state: str, action) -> tuple:
        edge = (state, action.key)
        self.visits[edge] = self.visits.get(edge, 0) + 1
        k = self._ikey(state, action)
        self.inst[k] = self.inst.get(k, 0) + 1
        return edge

    @staticmethod
    def _ikey(state: str, action) -> tuple:
        # un link lleva al mismo destino desde cualquier página -> su novedad es global (evita rebotar por el menú)
        return (None if action.kind == "link" else state, action.ident)

    def deposit(self, edge: tuple, amount: float) -> None:
        self.tau[edge] = min(self.cfg.tau_max, self.get(edge) + amount)

    def evaporate(self) -> None:
        for e in self.tau:
            self.tau[e] = max(self.cfg.tau_min, self.tau[e] * (1 - self.cfg.rho))

    def total(self) -> float:
        return sum(self.tau.values())

    def save(self, path: str) -> None:
        data = {SEP.join(e): [t, self.visits.get(e, 0), self.dest.get(e, "")] for e, t in self.tau.items()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, ensure_ascii=False)

    def load(self, path: str) -> None:
        with open(path, encoding="utf-8") as f:
            for k, (t, v, d) in json.load(f).items():
                edge = tuple(k.split(SEP))
                self.tau[edge], self.visits[edge] = t, v
                if d:
                    self.dest[edge] = d
