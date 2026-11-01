from flask import Blueprint, render_template

inicio_bp = Blueprint("inicio", __name__)


@inicio_bp.get("/")
def index():
    from app.routes.productos import productos_con_mysql

    return render_template("home/index.html", products=productos_con_mysql()[:4])
