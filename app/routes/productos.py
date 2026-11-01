from flask import Blueprint, render_template

from app.catalog import PRODUCTS
from app.db import query

productos_bp = Blueprint("productos", __name__)

CATEGORIAS_WEB = {"leche", "yogurt", "queso", "mantequilla", "crema"}

IMAGENES = {
    "leche": "https://images.unsplash.com/photo-1550583724-b2692b85b150?auto=format&fit=crop&w=900&q=85",
    "yogurt": "https://images.unsplash.com/photo-1488477181946-6428a0291777?auto=format&fit=crop&w=900&q=85",
    "queso": "https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?auto=format&fit=crop&w=900&q=85",
}
IMAGEN_DEFECTO = IMAGENES["leche"]


def productos_con_mysql():
    """Catálogo visual de catalog.py enriquecido con las tablas producto/inventario.

    Los productos que solo existen en MySQL también se agregan al final.
    """
    productos = [dict(p) for p in PRODUCTS]
    try:
        filas = query(
            "SELECT p.identificador, p.nombre, p.categoria, p.detalle, "
            "p.descripcion, p.precio, p.imagen_url, p.activo, "
            "COALESCE(i.stock, 0) AS stock, "
            "COALESCE(i.stock_minimo, 5) AS stock_minimo "
            "FROM producto p "
            "LEFT JOIN inventario i ON i.identificador_producto = p.identificador "
            "ORDER BY p.identificador"
        )
    except Exception as e:
        # Si MySQL está apagado, la web sigue funcionando con catalog.py.
        print("No se pudo leer MySQL:", e)
        filas = []

    por_nombre = {(f["nombre"] or "").strip().casefold(): f for f in filas}
    nombres_catalogo = {p["name"].strip().casefold() for p in productos}

    # 1) Productos de catalog.py: precio, stock y datos editables desde MySQL.
    visibles = []
    for p in productos:
        fila = por_nombre.get(p["name"].strip().casefold())
        if fila and not fila["activo"]:
            continue

        if not fila:
            p["stock"] = 0
            p["stock_minimo"] = 0
            p["agotado"] = True
            p["id_producto"] = None
            visibles.append(p)
            continue

        p["price"] = float(fila["precio"])
        p["stock"] = int(fila["stock"] or 0)
        p["stock_minimo"] = int(fila["stock_minimo"] or 0)
        p["agotado"] = p["stock"] <= 0
        p["id_producto"] = fila["identificador"]
        if fila.get("detalle"):
            p["detail"] = fila["detalle"]
        if fila.get("descripcion"):
            p["description"] = fila["descripcion"]
        if fila.get("imagen_url"):
            p["image"] = fila["imagen_url"]
        visibles.append(p)

    productos = visibles

    # 2) Productos nuevos (solo en MySQL): se agregan completos.
    for f in filas:
        if not f["activo"]:
            continue
        if (f["nombre"] or "").strip().casefold() in nombres_catalogo:
            continue

        categoria = (f["categoria"] or "").lower()
        if categoria not in CATEGORIAS_WEB:
            categoria = "otros"
        stock = int(f["stock"] or 0)
        detalle = (f.get("detalle") or f.get("descripcion") or "").strip()

        productos.append(
            {
                "id": f"db-{f['identificador']}",
                "id_producto": f["identificador"],
                "name": f["nombre"],
                "detail": detalle,
                "description": f.get("descripcion") or "",
                "category": categoria,
                "price": float(f["precio"]),
                "featured": False,
                "rating": 0,
                "stock": stock,
                "stock_minimo": int(f["stock_minimo"] or 0),
                "agotado": stock <= 0,
                "image": f.get("imagen_url") or IMAGENES.get(categoria, IMAGEN_DEFECTO),
                "alt": f["nombre"],
            }
        )

    return productos


@productos_bp.get("/productos")
def productos():
    return render_template("products/productos.html", products=productos_con_mysql())
