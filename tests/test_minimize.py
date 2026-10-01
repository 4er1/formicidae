from formicidae import minimize as m


def test_minimize_quita_un_desvio_de_varios_pasos(monkeypatch):
    # camino de 7 pasos; solo A, F y G hacen falta (y en ese orden). El desvío B-C-D-E es un bloque de 4.
    path = [{"id": c} for c in "ABCDEFG"]

    def fake(browser, cfg, cand, sig):
        return [d["id"] for d in cand if d["id"] in "AFG"] == list("AFG")

    monkeypatch.setattr(m, "reproduces", fake)
    assert [d["id"] for d in m.minimize(None, None, path, "x")] == list("AFG")


def test_minimize_conserva_lo_imprescindible(monkeypatch):
    path = [{"id": c} for c in "ABC"]
    monkeypatch.setattr(m, "reproduces", lambda b, c, cand, s: cand == path)
    assert m.minimize(None, None, path, "x") == path
