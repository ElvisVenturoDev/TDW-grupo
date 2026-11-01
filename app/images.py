"""Mapa central de las imágenes locales del proyecto.

Todas las fotos viven en ``app/static/img``. Si cambias una foto, solo
actualiza el nombre aquí y se reflejará en el catálogo, el carrusel y las
distintas secciones del sitio.
"""

STATIC_IMG = "/static/img/"


def img(filename):
    """Devuelve la URL pública de una imagen de ``app/static/img``."""
    return f"{STATIC_IMG}{filename}"


# --- Carrusel principal (inicio) -------------------------------------------
HERO_IMAGES = [
    img("vaca_carrusel_hero.avif"),
    img("vaca2_carrusel.avif"),
    img("verduras_carrusel.avif"),
]

# --- Imágenes de secciones -------------------------------------------------
CASA_IMAGE = img("imgCasa.avif")

# --- Catálogo --------------------------------------------------------------
# Foto principal por producto (id definido en app/catalog.py).
PRODUCT_IMAGES = {
    "leche-entera-fresca": img("img1_productos.avif"),
    "leche-semidescremada": img("img2_productos.avif"),
    # Sin foto propia todavía: comparte la imagen de leche.
    "leche-descremada": img("img1_productos.avif"),
    "yogurt-natural": img("img4_productos.avif"),
    # Sin foto propia todavía: comparten la imagen de yogurt.
    "yogurt-frutilla": img("img4_productos.avif"),
    "yogurt-mermelada": img("img4_productos.avif"),
    "queso-fresco": img("img7_productos.avif"),
    "queso-madurado": img("img8_productos.avif"),
    "queso-ricotta": img("img9_productos.avif"),
}

# Respaldo por categoría para productos que solo existen en MySQL.
CATEGORY_IMAGES = {
    "leche": img("img1_productos.avif"),
    "yogurt": img("img4_productos.avif"),
    "queso": img("img7_productos.avif"),
    "mantequilla": img("img8_productos.avif"),
    "crema": img("img9_productos.avif"),
}

DEFAULT_PRODUCT_IMAGE = img("img2_productos.avif")


def product_image(product_id=None, category=None):
    """Resuelve la foto de un producto por su id o, si no hay, por categoría."""
    if product_id and product_id in PRODUCT_IMAGES:
        return PRODUCT_IMAGES[product_id]
    if category:
        return CATEGORY_IMAGES.get((category or "").lower(), DEFAULT_PRODUCT_IMAGE)
    return DEFAULT_PRODUCT_IMAGE
