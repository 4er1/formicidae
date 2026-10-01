"""ShopLab: tienda demo con bugs plantados para probar Formicidae.

DEMO_FIXED=1 desactiva todos los bugs (sirve para comprobar que los tests generados pasan al corregirlos).
"""
import argparse
import base64
import logging
import os
import time

from flask import Flask, abort, redirect, render_template_string, request

FIXED = os.environ.get("DEMO_FIXED") == "1"
app = Flask(__name__, static_folder=None)

PRODUCTS = {i: (n, p) for i, (n, p) in enumerate(
    [("Teclado mecánico", 89), ("Mouse inalámbrico", 39), ("Monitor 27''", 249), ("Webcam HD", 59),
     ("Auriculares", 79), ("Hub USB-C", 35), ("Silla ergonómica", 189), ("Lámpara LED", 25)], start=1)}
REVIEWS = {i: [4, 5, 3] for i in PRODUCTS if i != 7}  # el producto 7 no tiene reseñas
CART: list = []
POSTS = {"hola-mundo": "Primer post.", "aco-testing": "Hormigas que testean."}
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

LAYOUT = """<!doctype html><html lang="es"><head><meta charset="utf-8"><title>ShopLab · {{ title }}</title>{{ head|safe }}</head>
<body><nav><a href="/">Inicio</a> | <a href="/products">Productos</a> | <a href="/search">Buscar</a> |
<a href="/blog">Blog</a> | <a href="/about">Nosotros</a> | <a href="/contact">Contacto</a> | <a href="/faq">FAQ</a> |
<a href="/cart">Carrito ({{ n }})</a></nav><hr>{{ body|safe }}</body></html>"""


def page(title, body, head=""):
    return render_template_string(LAYOUT, title=title, body=body, head=head, n=len(CART))


@app.route("/")
def home():
    return page("Inicio", "<h1>ShopLab</h1><p>Tienda demo.</p><a href='/report'>Reporte mensual</a>")


@app.route("/products")
def products():
    items = "".join(f'<li><a href="/products/{i}">{n}</a> — ${p}</li>' for i, (n, p) in PRODUCTS.items())
    return page("Productos", f"<h1>Productos</h1><ul>{items}</ul>")


@app.route("/products/<int:pid>")
def product(pid):
    if pid not in PRODUCTS:
        abort(404)
    name, price = PRODUCTS[pid]
    body = (f'<h1>{name}</h1><p>${price}</p><a href="/products/{pid}/reviews">Ver reseñas</a>'
            f'<form action="/cart/add" method="post"><input type="hidden" name="pid" value="{pid}">'
            f'<label>Cantidad <input type="number" name="qty" value="1"></label><button type="submit">Agregar</button></form>')
    return page(name, body)


@app.route("/products/<int:pid>/reviews")
def reviews(pid):
    rs = REVIEWS.get(pid, [])
    if not rs and FIXED:
        return page("Reseñas", "<h1>Reseñas</h1><p>Sin reseñas todavía.</p>")
    avg = sum(rs) / len(rs)  # BUG: ZeroDivisionError cuando no hay reseñas (producto 7)
    return page("Reseñas", f"<h1>Reseñas</h1><p>Promedio: {avg:.1f}</p>")


@app.route("/search")
def search():
    q = request.args.get("q", "")
    if "'" in q and not FIXED:
        raise RuntimeError("SQL syntax error near '''")  # BUG: 500 con comillas simples
    hits = [n for n, _ in PRODUCTS.values() if q.lower() in n.lower()] if q else []
    form = '<form action="/search" method="get"><input type="search" name="q"><button type="submit">Buscar</button></form>'
    return page("Buscar", f"<h1>Buscar</h1>{form}<p>{len(hits)} resultado(s)</p>")


@app.route("/cart/add", methods=["POST"])
def cart_add():
    qty = int(request.form["qty"])
    if FIXED:
        qty = max(1, min(qty, 99))
    elif qty <= 0:
        raise ValueError("cantidad inválida")  # BUG: sin validación de cantidad
    CART.append((int(request.form["pid"]), qty))
    return redirect("/cart")


@app.route("/cart")
def cart():
    return page("Carrito", f'<h1>Carrito</h1><p>{len(CART)} línea(s)</p><a href="/checkout">Pagar</a>')


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if request.method == "POST":
        return page("Gracias", "<h1>¡Gracias por tu compra!</h1>")
    form = '<form action="/checkout" method="post"><input type="email" name="email"><button type="submit">Confirmar</button></form>'
    return page("Pago", f"<h1>Pago</h1>{form}")


@app.route("/blog")
def blog():
    items = "".join(f'<li><a href="/blog/{s}">{s}</a></li>' for s in POSTS)
    if not FIXED:
        items += '<li><a href="/blog/old-post">Post antiguo</a></li>'  # BUG: enlace roto
    return page("Blog", f"<h1>Blog</h1><ul>{items}</ul>")


@app.route("/blog/<slug>")
def post(slug):
    if slug not in POSTS:
        abort(404)
    return page(slug, f"<h1>{slug}</h1><p>{POSTS[slug]}</p>")


@app.route("/about")
def about():
    return page("Nosotros", '<h1>Nosotros</h1><img src="/static/team.png" alt="Equipo" width="120" height="60">')


@app.route("/static/team.png")
def team_png():
    if not FIXED:
        abort(404)  # BUG: imagen rota
    return app.response_class(PNG, mimetype="image/png")


@app.route("/contact")
def contact():
    script = "<script>function sendMessage(){document.title='enviado';}</script>" if FIXED else ""
    return page("Contacto", f'<h1>Contacto</h1><button type="button" onclick="sendMessage()">Enviar mensaje</button>{script}')
    # BUG (sin FIXED): sendMessage no está definida -> ReferenceError al hacer clic


@app.route("/faq")
def faq():
    script = "" if FIXED else "<script>console.error('Config de FAQ no cargada')</script>"  # BUG: error en consola
    return page("FAQ", "<h1>Preguntas frecuentes</h1><p>Todo bien por aquí.</p>", head=script)


@app.route("/report")
def report():
    if not FIXED:
        time.sleep(float(os.environ.get("DEMO_SLOW_SECONDS", "3.2")))  # BUG: endpoint lento
    return page("Reporte", "<h1>Reporte mensual</h1>")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5000)
    a = ap.parse_args()
    logging.getLogger("werkzeug").setLevel(logging.CRITICAL)
    app.run(host="127.0.0.1", port=a.port, threaded=True)
