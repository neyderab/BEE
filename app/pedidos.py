"""Estados de los pedidos, notificaciones y consultas compartidas."""

from datetime import datetime, timedelta

from app.db import conectar

# Orden en que avanza un pedido. "cancelado" puede ocurrir antes de "listo".
ESTADOS = {
    "pendiente": "Esperando confirmación",
    "aceptado": "Aceptado",
    "preparando": "En preparación",
    "listo": "Listo para recoger",
    "entregado": "Entregado",
    "cancelado": "Cancelado",
}

# Pasos que se muestran en la barra de progreso del estudiante.
PASOS = ["pendiente", "aceptado", "preparando", "listo", "entregado"]

# Cambios de estado que puede hacer la tienda desde cada estado.
TRANSICIONES = {
    "pendiente": ["aceptado", "cancelado"],
    "aceptado": ["preparando", "cancelado"],
    "preparando": ["listo", "cancelado"],
    "listo": ["entregado"],
    "entregado": [],
    "cancelado": [],
}

# Texto del botón que lleva a cada estado.
ACCIONES = {
    "aceptado": "Aceptar pedido",
    "preparando": "Empezar a preparar",
    "listo": "Marcar como listo",
    "entregado": "Marcar como entregado",
    "cancelado": "Cancelar",
}

ACTIVOS = ("pendiente", "aceptado", "preparando", "listo")

# Opciones de tiempo de preparación: 5 -> "5–10 min", ..., 25 -> "25–30 min".
TIEMPOS = (5, 10, 15, 20, 25)
RANGO_MINUTOS = 5


def texto_tiempo(tiempo_min: int) -> str:
    return f"{tiempo_min}–{tiempo_min + RANGO_MINUTOS} min"


def ventana_recogida(pedido: dict) -> tuple[datetime, datetime] | None:
    """Desde cuándo y hasta cuándo se puede recoger un pedido aceptado."""
    if pedido.get("aceptado_en") is None or pedido.get("tiempo_min") is None:
        return None
    inicio = pedido["aceptado_en"]
    return (
        inicio + timedelta(minutes=pedido["tiempo_min"]),
        inicio + timedelta(minutes=pedido["tiempo_max"]),
    )


# ---------- Notificaciones ----------

def notificar(conexion, usuario_id: int | None, texto: str, pedido_id: int | None = None):
    """Crea una notificación dentro de la transacción de `conexion`."""
    if usuario_id is None:  # El estudiante cerró su cuenta.
        return
    conexion.execute(
        "INSERT INTO notificaciones (usuario_id, pedido_id, texto) VALUES (%s, %s, %s)",
        (usuario_id, pedido_id, texto[:200]),
    )


def mensaje_para_estudiante(estado: str, pedido_id: int, tienda: str, tiempo_min: int | None):
    if estado == "aceptado":
        espera = f" Estará listo en {texto_tiempo(tiempo_min)}." if tiempo_min else ""
        return f"{tienda} aceptó tu pedido #{pedido_id}.{espera}"
    if estado == "preparando":
        return f"Tu pedido #{pedido_id} está en preparación."
    if estado == "listo":
        return f"¡Tu pedido #{pedido_id} está listo! Pásalo a recoger en {tienda}."
    if estado == "entregado":
        return f"Pedido #{pedido_id} entregado. ¡Buen provecho!"
    if estado == "cancelado":
        return f"{tienda} canceló tu pedido #{pedido_id}."
    return f"Tu pedido #{pedido_id} cambió de estado: {ESTADOS[estado]}."


def notificaciones_recientes(usuario_id: int, limite: int = 15) -> list[dict]:
    with conectar() as conexion:
        return conexion.execute(
            """
            SELECT id, pedido_id, texto, leida, creada_en
            FROM notificaciones
            WHERE usuario_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (usuario_id, limite),
        ).fetchall()


def contar_sin_leer(usuario_id: int) -> int:
    with conectar() as conexion:
        return conexion.execute(
            "SELECT COUNT(*) AS n FROM notificaciones WHERE usuario_id = %s AND NOT leida",
            (usuario_id,),
        ).fetchone()["n"]


# ---------- Consultas ----------

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
        pedido["ventana"] = ventana_recogida(pedido)
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
