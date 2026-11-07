"""Estados de los pedidos y consultas compartidas entre tienda y estudiante."""

from app.db import conectar

ESTADOS = {
    "pendiente": "Pendiente",
    "preparando": "En preparación",
    "listo": "Listo para recoger",
    "entregado": "Entregado",
    "cancelado": "Cancelado",
}

# Cambios de estado que puede hacer la tienda desde cada estado.
TRANSICIONES = {
    "pendiente": ["preparando", "cancelado"],
    "preparando": ["listo", "cancelado"],
    "listo": ["entregado"],
    "entregado": [],
    "cancelado": [],
}

ACTIVOS = ("pendiente", "preparando", "listo")


def agregar_items(pedidos: list[dict]) -> list[dict]:
    """Agrega a cada pedido la lista de sus productos (`items`)."""
    if not pedidos:
        return pedidos
    ids = [p["id"] for p in pedidos]
    with conectar() as conexion:
        filas = conexion.execute(
            """
            SELECT pedido_id, nombre_producto, precio_unitario, cantidad
            FROM pedido_items
            WHERE pedido_id = ANY(%s)
            ORDER BY id
            """,
            (ids,),
        ).fetchall()
    por_pedido: dict[int, list] = {i: [] for i in ids}
    for fila in filas:
        por_pedido[fila["pedido_id"]].append(fila)
    for pedido in pedidos:
        pedido["items"] = por_pedido[pedido["id"]]
    return pedidos


def menus_con_productos(tienda_id: int, solo_disponibles: bool = False) -> list[dict]:
    with conectar() as conexion:
        menus = conexion.execute(
            "SELECT id, nombre FROM menus WHERE tienda_id = %s ORDER BY id",
            (tienda_id,),
        ).fetchall()
        productos = conexion.execute(
            """
            SELECT p.id, p.menu_id, p.nombre, p.descripcion, p.precio, p.disponible
            FROM productos p
            JOIN menus m ON m.id = p.menu_id
            WHERE m.tienda_id = %s AND (p.disponible OR NOT %s)
            ORDER BY p.nombre
            """,
            (tienda_id, solo_disponibles),
        ).fetchall()
    for menu in menus:
        menu["productos"] = [p for p in productos if p["menu_id"] == menu["id"]]
    if solo_disponibles:
        menus = [m for m in menus if m["productos"]]
    return menus
