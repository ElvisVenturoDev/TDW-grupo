import re

from flask import Blueprint, current_app, render_template, request

from app.db import get_db

contacto_bp = Blueprint("contacto", __name__)

CORREO_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
CELULAR_RE = re.compile(r"\+?\d{6,15}")


def _ip_cliente():
    forwarded = request.headers.get("X-Forwarded-For", "")
    return (forwarded.split(",")[0].strip() or request.remote_addr or "")[:45]


@contacto_bp.route("/contacto", methods=["GET", "POST"])
def contacto():
    if request.method == "POST":
        nombre = " ".join(request.form.get("nombre", "").split())
        celular = re.sub(r"[\s().-]+", "", request.form.get("celular", ""))
        correo = request.form.get("correo", "").strip().lower()
        asunto = request.form.get("asunto", "").strip()
        mensaje = request.form.get("mensaje", "").strip()

        error = None
        if not nombre or not celular or not mensaje:
            error = "Completa tu nombre, celular y mensaje."
        elif len(nombre) > 80:
            error = "El nombre no puede superar 80 caracteres."
        elif not CELULAR_RE.fullmatch(celular):
            error = "Ingresa un celular válido (solo números, máximo 15 caracteres)."
        elif correo and (len(correo) > 120 or not CORREO_RE.fullmatch(correo)):
            error = "Ingresa un correo válido."
        elif len(asunto) > 80:
            error = "El asunto no puede superar 80 caracteres."
        elif len(mensaje) > 5000:
            error = "El mensaje es demasiado largo (máximo 5000 caracteres)."

        if error:
            return (
                render_template(
                    "contact/contacto.html",
                    error=error,
                    enviado=False,
                    nombre=nombre,
                ),
                400,
            )

        db = None
        try:
            db = get_db()
            with db.cursor() as cur:
                cur.execute(
                    "INSERT INTO mensaje_contacto "
                    "(nombre, celular, correo, asunto, mensaje, ip, user_agent) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        nombre,
                        celular,
                        correo or None,
                        asunto or None,
                        mensaje,
                        _ip_cliente() or None,
                        request.headers.get("User-Agent", "")[:255] or None,
                    ),
                )
            db.commit()
        except Exception:
            if db is not None:
                db.rollback()
            current_app.logger.exception("No se pudo guardar el mensaje de contacto")
            return (
                render_template(
                    "contact/contacto.html",
                    error="No pudimos registrar tu mensaje. Inténtalo de nuevo en unos minutos.",
                    enviado=False,
                    nombre=nombre,
                ),
                503,
            )

        return render_template(
            "contact/contacto.html",
            enviado=True,
            nombre=nombre,
        )

    return render_template("contact/contacto.html", enviado=False, nombre="")
