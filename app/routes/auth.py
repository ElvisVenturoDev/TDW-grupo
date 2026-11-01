import re
from datetime import date

import pymysql
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from app.db import get_db, query

auth_bp = Blueprint("auth", __name__)

CORREO_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
TELEFONO_RE = re.compile(r"9\d{8}")


@auth_bp.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = " ".join(request.form.get("nombre", "").split())
        correo = request.form.get("correo", "").strip().lower()
        telefono = request.form.get("telefono", "").strip()
        password = request.form.get("password", "")
        confirmar = request.form.get("confirmar_password", "")

        errores = []
        if len(nombre.replace(" ", "")) < 3:
            errores.append("El nombre debe tener al menos 3 letras.")
        if len(nombre) > 80:
            errores.append("El nombre no puede superar 80 caracteres.")
        if not CORREO_RE.fullmatch(correo):
            errores.append("Ingresa un correo válido.")
        if len(correo) > 120:
            errores.append("El correo no puede superar 120 caracteres.")
        if telefono and not TELEFONO_RE.fullmatch(telefono):
            errores.append("El teléfono debe tener 9 dígitos y empezar con 9.")
        if len(password) < 6:
            errores.append("La contraseña debe tener al menos 6 caracteres.")
        if len(password) > 128:
            errores.append("La contraseña no puede superar 128 caracteres.")
        if password != confirmar:
            errores.append("Las contraseñas no coinciden.")

        existente = None
        if not errores:
            filas = query(
                "SELECT identificador, activo, password_hash "
                "FROM cliente WHERE correo = %s LIMIT 1",
                (correo,),
            )
            existente = filas[0] if filas else None
            if existente:
                if not existente["activo"]:
                    errores.append("La cuenta asociada a ese correo está desactivada.")
                elif existente["password_hash"]:
                    errores.append("Ya existe una cuenta con ese correo.")

        if errores:
            for e in errores:
                flash(e, "error")
            return render_template("authentication/registro.html", datos=request.form), 400

        db = get_db()
        try:
            with db.cursor() as cur:
                password_hash = generate_password_hash(password)

                if existente:
                    # Cliente creado antes desde un pedido: todavía no tenía contraseña.
                    id_cliente = existente["identificador"]
                    cur.execute(
                        "UPDATE cliente SET nombre = %s, telefono = %s, "
                        "password_hash = %s, activo = 1 WHERE identificador = %s",
                        (nombre, telefono or None, password_hash, id_cliente),
                    )
                else:
                    cur.execute(
                        "INSERT INTO cliente (nombre, telefono, correo, password_hash) "
                        "VALUES (%s, %s, %s, %s)",
                        (nombre, telefono or None, correo, password_hash),
                    )
                    id_cliente = cur.lastrowid

                cur.execute(
                    "INSERT INTO detalle_cliente "
                    "(identificador_cliente, direccion, tipo_cliente, fecha_registro) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE actualizado_en = CURRENT_TIMESTAMP",
                    (id_cliente, "Sin dirección", "Minorista", date.today()),
                )
            db.commit()
        except pymysql.err.IntegrityError:
            db.rollback()
            flash("Ya existe una cuenta con ese correo.", "error")
            return render_template("authentication/registro.html", datos=request.form), 400
        except Exception:
            db.rollback()
            current_app.logger.exception("Error creando la cuenta")
            flash("No pudimos crear la cuenta. Inténtalo de nuevo.", "error")
            return render_template("authentication/registro.html", datos=request.form), 503

        flash("¡Cuenta creada! Ahora inicia sesión para continuar.", "ok")
        return redirect(url_for("login.login"))

    return render_template("authentication/registro.html", datos={})
