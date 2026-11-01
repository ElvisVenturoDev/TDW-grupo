import json
import re
from datetime import date
from decimal import Decimal

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.catalog import PRODUCTS
from app.db import get_db

formulario_bp = Blueprint("formulario", __name__)

NOMBRE_RE = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü' ]{3,80}")
TELEFONO_RE = re.compile(r"9\d{8}")
CORREO_RE = re.compile(
    r"[a-z0-9._+\-]+@(gmail\.com|gmail\.com\.pe|hotmail\.com|outlook\.com|yahoo\.com|vallegrande\.edu\.pe)"
)
ENTREGAS_VALIDAS = ("entrega_domicilio", "recogida")


def _producto_attr(producto, clave, defecto=None):
    """Lee un dato del producto venga como diccionario u objeto."""
    if isinstance(producto, dict):
        return producto.get(clave, defecto)
    return getattr(producto, clave, defecto)


def _nombre_producto(p):
    return _producto_attr(p, "name", "")


def _productos_validos():
    from app.routes.productos import productos_con_mysql

    return {p["name"] for p in productos_con_mysql()}


def validar_pedido(f, productos=None):
    errores = []
    nombre = " ".join(f.get("nombre", "").split())
    telefono = f.get("telefono", "").strip()
    correo = f.get("correo", "").strip().lower()
    producto = f.get("producto", "")
    productos_carrito = f.get("productos_carrito", "")
    entrega = f.get("entrega") or "entrega_domicilio"
    direccion = f.get("direccion", "").strip()
    distrito = f.get("distrito", "").strip()
    comentarios = f.get("comentarios", "").strip()

    if not NOMBRE_RE.fullmatch(nombre) or len(nombre.replace(" ", "")) < 3:
        errores.append("El nombre debe tener al menos 3 letras (solo letras y espacios).")

    if len(nombre) > 80:
        errores.append("El nombre no puede superar 80 caracteres.")

    if not TELEFONO_RE.fullmatch(telefono):
        errores.append("El teléfono debe tener 9 dígitos y empezar con 9.")

    if len(correo) > 120:
        errores.append("El correo no puede superar 120 caracteres.")
    elif correo and not CORREO_RE.fullmatch(correo):
        errores.append("El correo debe estar en minúsculas y usar un dominio permitido (ej. @gmail.com).")

    if productos_carrito:
        try:
            cart_items = json.loads(productos_carrito)
            if not isinstance(cart_items, list) or len(cart_items) == 0:
                errores.append("El carrito está vacío.")
            else:
                nombres_validos = (
                    {p["name"] for p in productos}
                    if productos is not None
                    else _productos_validos()
                )
                for item in cart_items:
                    if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                        errores.append("Hay un producto con formato inválido en el carrito.")
                        continue
                    if item.get("name") not in nombres_validos:
                        errores.append(f"Producto no válido: {item.get('name', 'desconocido')}.")
                    if not isinstance(item.get("quantity"), int) or item.get("quantity", 0) < 1:
                        errores.append("Las cantidades deben ser números enteros de 1 o más.")
        except (json.JSONDecodeError, TypeError):
            errores.append("Error al procesar los productos del carrito.")
    else:
        nombres_validos = (
            {p["name"] for p in productos}
            if productos is not None
            else _productos_validos()
        )
        if producto not in nombres_validos:
            errores.append("Selecciona un producto válido.")

        try:
            if int(f.get("cantidad", "")) < 1:
                raise ValueError
        except (TypeError, ValueError):
            errores.append("La cantidad debe ser un número entero de 1 o más.")

    if entrega not in ENTREGAS_VALIDAS:
        errores.append("Selecciona una modalidad de entrega.")

    if len(direccion) > 180:
        errores.append("La dirección de entrega no puede superar 180 caracteres.")

    if len(distrito) > 60:
        errores.append("El distrito no puede superar 60 caracteres.")

    if entrega == "entrega_domicilio":
        if not direccion:
            errores.append("Ingresa la dirección de entrega.")
        if not distrito:
            errores.append("Ingresa el distrito o localidad.")

    if len(comentarios) > 300:
        errores.append("Los comentarios no pueden superar 300 caracteres.")

    if "confirmacion" in f and not f.get("confirmacion"):
        errores.append("Debes aceptar los términos para enviar el pedido.")

    return errores


def _items_del_pedido(f):
    """Devuelve [(nombre_producto, cantidad)] desde el carrito o el producto individual."""
    productos_carrito = f.get("productos_carrito", "")
    if productos_carrito:
        return [(i["name"], int(i["quantity"])) for i in json.loads(productos_carrito)]
    return [(f["producto"], int(f["cantidad"]))]


def _guardar_detalle(cur, id_cliente, direccion, distrito, actualizar):
    if actualizar:
        cur.execute(
            "INSERT INTO detalle_cliente "
            "(identificador_cliente, direccion, distrito, tipo_cliente, fecha_registro) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE "
            "direccion = VALUES(direccion), distrito = VALUES(distrito), "
            "tipo_cliente = VALUES(tipo_cliente), actualizado_en = CURRENT_TIMESTAMP",
            (id_cliente, direccion, distrito, "Minorista", date.today()),
        )
    else:
        cur.execute(
            "INSERT INTO detalle_cliente "
            "(identificador_cliente, direccion, distrito, tipo_cliente, fecha_registro) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE actualizado_en = CURRENT_TIMESTAMP",
            (id_cliente, direccion, distrito, "Minorista", date.today()),
        )


def guardar_pedido(f):
    """Guarda el pedido en venta/detalle_venta y reserva stock si alcanza."""
    nombre = " ".join(f["nombre"].split())
    telefono = f["telefono"].strip()
    correo = f.get("correo", "").strip().lower() or None
    entrega = f.get("entrega", "entrega_domicilio")
    direccion = f.get("direccion", "").strip()[:180] or None
    distrito = f.get("distrito", "").strip()[:60] or None
    comentarios = f.get("comentarios", "").strip()[:300] or None

    if entrega == "recogida":
        direccion_entrega = "Recojo en tienda"
        distrito_entrega = None
        detalle_direccion = "Sin dirección"
        detalle_distrito = None
    else:
        direccion_entrega = direccion or "Sin dirección"
        distrito_entrega = distrito
        detalle_direccion = direccion or "Sin dirección"
        detalle_distrito = distrito

    db = get_db()
    try:
        with db.cursor() as cur:
            # 1. Buscar cliente existente (por correo o teléfono) o crearlo.
            if correo:
                cur.execute(
                    "SELECT identificador, activo FROM cliente "
                    "WHERE correo = %s OR telefono = %s "
                    "ORDER BY (correo = %s) DESC, identificador LIMIT 1",
                    (correo, telefono, correo),
                )
            else:
                cur.execute(
                    "SELECT identificador, activo FROM cliente "
                    "WHERE telefono = %s ORDER BY identificador LIMIT 1",
                    (telefono,),
                )
            fila = cur.fetchone()

            if fila and not fila["activo"]:
                raise ValueError("La cuenta asociada a estos datos está desactivada.")

            if fila:
                id_cliente = fila["identificador"]
                cur.execute(
                    "UPDATE cliente SET nombre = %s, telefono = %s, "
                    "correo = COALESCE(correo, %s) WHERE identificador = %s",
                    (nombre, telefono, correo, id_cliente),
                )
                _guardar_detalle(
                    cur,
                    id_cliente,
                    detalle_direccion,
                    detalle_distrito,
                    actualizar=entrega == "entrega_domicilio",
                )
            else:
                # El cliente aún no tiene contraseña; /registro la establece después.
                cur.execute(
                    "INSERT INTO cliente (nombre, telefono, correo, password_hash) "
                    "VALUES (%s, %s, %s, %s)",
                    (nombre, telefono, correo, ""),
                )
                id_cliente = cur.lastrowid
                _guardar_detalle(
                    cur,
                    id_cliente,
                    detalle_direccion,
                    detalle_distrito,
                    actualizar=False,
                )

            # 2. Crear la venta con todos los datos del esquema.
            cur.execute(
                "INSERT INTO venta "
                "(fecha, identificador_cliente, tipo_entrega, direccion_entrega, "
                "distrito, comentarios, estado, canal) "
                "VALUES (%s, %s, %s, %s, %s, %s, 'pendiente', 'web')",
                (
                    date.today(),
                    id_cliente,
                    entrega,
                    direccion_entrega,
                    distrito_entrega,
                    comentarios,
                ),
            )
            id_venta = cur.lastrowid

            # 3. Guardar productos; reservar stock solo si alcanza.
            total = Decimal("0.00")
            for nombre_prod, cantidad in _items_del_pedido(f):
                cur.execute(
                    "SELECT identificador, precio, activo, detalle, descripcion, imagen_url "
                    "FROM producto WHERE nombre = %s LIMIT 1",
                    (nombre_prod,),
                )
                prod = cur.fetchone()
                if prod and not prod["activo"]:
                    raise ValueError(f"El producto «{nombre_prod}» no está disponible.")

                if not prod:
                    producto_catalogo = next(
                        (p for p in PRODUCTS if _nombre_producto(p) == nombre_prod),
                        None,
                    )
                    if not producto_catalogo:
                        raise ValueError(
                            f"El producto «{nombre_prod}» no está disponible en el catálogo."
                        )

                    categoria = (_producto_attr(producto_catalogo, "category", "otros") or "otros")[:50]
                    detalle = (_producto_attr(producto_catalogo, "detail", "") or "")[:80] or None
                    descripcion = _producto_attr(producto_catalogo, "description", None)
                    imagen_url = _producto_attr(producto_catalogo, "image", None)
                    precio = _producto_attr(producto_catalogo, "price", 0)

                    cur.execute(
                        "INSERT INTO producto "
                        "(nombre, categoria, detalle, descripcion, precio, imagen_url) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (
                            _nombre_producto(producto_catalogo),
                            categoria,
                            detalle,
                            descripcion,
                            precio,
                            imagen_url,
                        ),
                    )
                    prod = {
                        "identificador": cur.lastrowid,
                        "precio": precio,
                        "activo": 1,
                    }
                    cur.execute(
                        "INSERT INTO inventario "
                        "(identificador_producto, stock, stock_minimo) "
                        "VALUES (%s, 0, 5)",
                        (prod["identificador"],),
                    )
                else:
                    # Si el producto no tenía fila de inventario, se crea en 0.
                    cur.execute(
                        "INSERT INTO inventario "
                        "(identificador_producto, stock, stock_minimo) "
                        "VALUES (%s, 0, 5) "
                        "ON DUPLICATE KEY UPDATE "
                        "identificador_producto = VALUES(identificador_producto)",
                        (prod["identificador"],),
                    )

                cur.execute(
                    "SELECT stock FROM inventario "
                    "WHERE identificador_producto = %s LIMIT 1 FOR UPDATE",
                    (prod["identificador"],),
                )
                inventario = cur.fetchone()
                if inventario and inventario["stock"] >= cantidad:
                    cur.execute(
                        "UPDATE inventario SET stock = stock - %s "
                        "WHERE identificador_producto = %s AND stock >= %s",
                        (cantidad, prod["identificador"], cantidad),
                    )

                cur.execute(
                    "INSERT INTO detalle_venta "
                    "(identificador_venta, identificador_producto, cantidad, precio_unitario) "
                    "VALUES (%s, %s, %s, %s)",
                    (id_venta, prod["identificador"], cantidad, prod["precio"]),
                )
                total += Decimal(str(prod["precio"])) * cantidad

            cur.execute(
                "UPDATE venta SET total = %s WHERE identificador = %s",
                (total, id_venta),
            )
        db.commit()
        return id_venta
    except Exception:
        db.rollback()
        raise


@formulario_bp.route("/formulario", methods=["GET", "POST"])
def formulario():
    from app.routes.productos import productos_con_mysql

    products = productos_con_mysql()

    if request.method == "POST":
        errores = validar_pedido(request.form, products)

        if not errores:
            try:
                guardar_pedido(request.form)
            except ValueError as e:
                errores.append(str(e))
            except Exception:
                current_app.logger.exception("Error inesperado guardando pedido")
                errores.append("No pudimos registrar tu pedido. Inténtalo de nuevo.")

        if errores:
            for e in errores:
                flash(e, "error")
            return (
                render_template(
                    "orders/formulario.html",
                    products=products,
                    producto_seleccionado=request.form.get("producto", ""),
                    datos=request.form,
                ),
                400,
            )

        flash(
            "¡Pedido recibido! Confirmaremos la disponibilidad y entrega por WhatsApp.",
            "ok",
        )
        return redirect(url_for("formulario.pedido_registrado"))

    return render_template(
        "orders/formulario.html",
        products=products,
        producto_seleccionado=request.args.get("producto", ""),
        datos={},
    )


@formulario_bp.route("/pedido-registrado")
def pedido_registrado():
    return render_template("orders/pedido_registrado.html")
