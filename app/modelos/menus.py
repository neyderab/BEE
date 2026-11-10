"""Menús y productos de una tienda.

Todas las funciones que cambian algo reciben `tienda_id` y solo afectan menús
y productos de esa tienda. Devuelven la fila afectada, o None si no existe
(o es de otra tienda).
"""

import re

from app.modelos.base_datos import campos_foto, todos, uno

PRECIO_MAXIMO = 10_000_000

# Condición para que solo se modifiquen productos de la tienda indicada.
_DE_LA_TIENDA = "menu_id IN (SELECT id FROM menus WHERE tienda_id = %s)"


# ---------- Reglas ----------

def leer_precio(texto: str) -> int | None:
    """Acepta '12500', '12.500' o '$ 12,500'. Devuelve None si no es válido."""
    limpio = re.sub(r"[\s$.,]", "", texto)
    if not limpio.isdigit():
        return None
    precio = int(limpio)
    return precio if 0 < precio <= PRECIO_MAXIMO else None


def validar_producto(nombre: str, descripcion: str, precio: str):
    """Devuelve ((nombre, descripcion, precio), None) o (None, mensaje de error)."""
    nombre, descripcion, valor = nombre.strip(), descripcion.strip(), leer_precio(precio)
    if not nombre or len(nombre) > 80:
        return None, "El nombre del producto es obligatorio (máximo 80 caracteres)."
    if len(descripcion) > 200:
        return None, "La descripción admite máximo 200 caracteres."
    if valor is None:
        return None, "Escribe un precio válido en pesos, por ejemplo 4500."
    return (nombre, descripcion, valor), None


# ---------- Consultas ----------

def menus_con_productos(tienda_id: int, solo_disponibles: bool = False) -> list[dict]:
    menus = todos("SELECT id, nombre FROM menus WHERE tienda_id = %s ORDER BY id", (tienda_id,))
    productos = todos(
        f"""
        SELECT p.id, p.menu_id, p.nombre, p.descripcion, p.precio, p.disponible, {campos_foto("p")}
        FROM productos p JOIN menus m ON m.id = p.menu_id
        WHERE m.tienda_id = %s AND (p.disponible OR NOT %s)
        ORDER BY p.nombre
        """,
        (tienda_id, solo_disponibles),
    )
    for menu in menus:
        menu["productos"] = [p for p in productos if p["menu_id"] == menu["id"]]
    return [m for m in menus if m["productos"]] if solo_disponibles else menus


def foto_producto(producto_id: int) -> dict | None:
    return uno("SELECT foto FROM productos WHERE id = %s AND foto IS NOT NULL", (producto_id,))


# ---------- Menús ----------

def crear_menu(tienda_id: int, nombre: str) -> dict:
    return uno("INSERT INTO menus (tienda_id, nombre) VALUES (%s, %s) RETURNING nombre", (tienda_id, nombre))


def eliminar_menu(tienda_id: int, menu_id: int) -> dict | None:
    return uno("DELETE FROM menus WHERE id = %s AND tienda_id = %s RETURNING nombre", (menu_id, tienda_id))


# ---------- Productos ----------

def crear_producto(tienda_id: int, menu_id: int, nombre: str, descripcion: str, precio: int) -> dict | None:
    return uno(
        """
        INSERT INTO productos (menu_id, nombre, descripcion, precio)
        SELECT id, %s, %s, %s FROM menus WHERE id = %s AND tienda_id = %s
        RETURNING nombre
        """,
        (nombre, descripcion, precio, menu_id, tienda_id),
    )


def editar_producto(tienda_id: int, producto_id: int, nombre: str, descripcion: str, precio: int) -> dict | None:
    return uno(
        f"""
        UPDATE productos SET nombre = %s, descripcion = %s, precio = %s
        WHERE id = %s AND {_DE_LA_TIENDA} RETURNING nombre
        """,
        (nombre, descripcion, precio, producto_id, tienda_id),
    )


def alternar_disponible(tienda_id: int, producto_id: int) -> dict | None:
    return uno(
        f"UPDATE productos SET disponible = NOT disponible WHERE id = %s AND {_DE_LA_TIENDA} RETURNING nombre, disponible",
        (producto_id, tienda_id),
    )


def eliminar_producto(tienda_id: int, producto_id: int) -> dict | None:
    return uno(f"DELETE FROM productos WHERE id = %s AND {_DE_LA_TIENDA} RETURNING nombre", (producto_id, tienda_id))


def guardar_foto_producto(tienda_id: int, producto_id: int, jpeg: bytes | None) -> dict | None:
    """Guarda la foto del producto, o la quita si `jpeg` es None."""
    if jpeg is None:
        return uno(
            f"UPDATE productos SET foto = NULL, foto_actualizada = NULL WHERE id = %s AND {_DE_LA_TIENDA} RETURNING nombre",
            (producto_id, tienda_id),
        )
    return uno(
        f"UPDATE productos SET foto = %s, foto_actualizada = now() WHERE id = %s AND {_DE_LA_TIENDA} RETURNING nombre",
        (jpeg, producto_id, tienda_id),
    )
