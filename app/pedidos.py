"""Pedidos: estados, tiempos, horario de las tiendas, pagos y notificaciones."""

import secrets
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.db import campos_foto, todos, uno

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
    "listo": [],  # Se entrega solo con el código de recogida (ver entregar_con_codigo).
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


ZONA_HORARIA = ZoneInfo("America/Bogota")

# Métodos de pago: (nombre, disponible). Por ahora solo se acepta efectivo.
METODOS_PAGO = {
    "efectivo": ("Efectivo", True),
    "nequi": ("Nequi", False),
    "debito": ("Tarjeta débito", False),
    "credito": ("Tarjeta crédito", False),
}
METODO_PREDETERMINADO = "efectivo"


def metodo_disponible(metodo: str) -> bool:
    return METODOS_PAGO.get(metodo, ("", False))[1]


# ---------- Horario de las tiendas ----------

def tienda_abierta(tienda: dict, ahora: datetime | None = None) -> bool:
    """Abierta si su interruptor está encendido y, si tiene horario, está dentro de él."""
    if not tienda.get("abierta"):
        return False
    apertura, cierre = tienda.get("hora_apertura"), tienda.get("hora_cierre")
    if apertura is None or cierre is None:
        return True
    hora = (ahora or datetime.now(ZONA_HORARIA)).astimezone(ZONA_HORARIA).time()
    if apertura <= cierre:
        return apertura <= hora < cierre
    return hora >= apertura or hora < cierre  # Horario que pasa la medianoche.


def estado_tienda(tienda: dict) -> str:
    """Texto corto para el estudiante, por ejemplo «Cierra a las 18:00»."""
    apertura, cierre = tienda.get("hora_apertura"), tienda.get("hora_cierre")
    if tienda_abierta(tienda):
        return f"Cierra a las {cierre:%H:%M}" if cierre else "Recibiendo pedidos"
    if tienda.get("abierta") and apertura:
        return f"Abre a las {apertura:%H:%M}"
    return "No recibe pedidos por ahora"


def leer_hora(texto: str) -> time | None:
    try:
        return time.fromisoformat(texto.strip())
    except ValueError:
        return None


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

def notificar(conexion, usuario_id: int | None, texto: str, pedido_id: int | None = None, url: str = "/app"):
    """Crea una notificación (campana) y la envía como aviso push al celular."""
    if usuario_id is None:  # El estudiante cerró su cuenta.
        return
    conexion.execute(
        "INSERT INTO notificaciones (usuario_id, pedido_id, texto) VALUES (%s, %s, %s)",
        (usuario_id, pedido_id, texto[:200]),
    )
    from app.push import enviar_en_segundo_plano  # Evita una importación circular.

    enviar_en_segundo_plano(usuario_id, texto, url)


# ---------- Código de recogida ----------

def generar_codigo(conexion, tienda_id: int) -> str:
    """Código de 4 dígitos que no repite el de otro pedido listo de la misma tienda."""
    en_uso = {
        f["codigo_recogida"]
        for f in conexion.execute(
            "SELECT codigo_recogida FROM pedidos WHERE tienda_id = %s AND estado = 'listo'", (tienda_id,)
        )
    }
    while True:
        codigo = f"{secrets.randbelow(10000):04d}"
        if codigo not in en_uso:
            return codigo


def mensaje_para_estudiante(
    estado: str, pedido_id: int, tienda: str, tiempo_min: int | None, codigo: str | None = None
):
    if estado == "aceptado":
        espera = f" Estará listo en {texto_tiempo(tiempo_min)}." if tiempo_min else ""
        return f"{tienda} aceptó tu pedido #{pedido_id}.{espera}"
    if estado == "preparando":
        return f"Tu pedido #{pedido_id} está en preparación."
    if estado == "listo":
        con_codigo = f" Muestra el código {codigo}" if codigo else " Pásalo a recoger"
        return f"🐝 ¡Tu pedido #{pedido_id} está listo!{con_codigo} en {tienda}."
    if estado == "entregado":
        return f"Pedido #{pedido_id} entregado. ¡Buen provecho!"
    if estado == "cancelado":
        return f"{tienda} canceló tu pedido #{pedido_id}."
    return f"Tu pedido #{pedido_id} cambió de estado: {ESTADOS[estado]}."


def notificaciones_recientes(usuario_id: int, limite: int = 15) -> list[dict]:
    return todos(
        """
        SELECT id, pedido_id, texto, leida, creada_en FROM notificaciones
        WHERE usuario_id = %s ORDER BY id DESC LIMIT %s
        """,
        (usuario_id, limite),
    )


def contar_sin_leer(usuario_id: int) -> int:
    return uno(
        "SELECT COUNT(*) AS n FROM notificaciones WHERE usuario_id = %s AND NOT leida", (usuario_id,)
    )["n"]


# ---------- Consultas ----------

def agregar_items(pedidos: list[dict]) -> list[dict]:
    """Agrega a cada pedido la lista de sus productos (`items`)."""
    if not pedidos:
        return pedidos
    ids = [p["id"] for p in pedidos]
    por_pedido: dict[int, list] = {i: [] for i in ids}
    for fila in todos(
        """
        SELECT pedido_id, nombre_producto, precio_unitario, cantidad
        FROM pedido_items WHERE pedido_id = ANY(%s) ORDER BY id
        """,
        (ids,),
    ):
        por_pedido[fila["pedido_id"]].append(fila)
    for pedido in pedidos:
        pedido["items"] = por_pedido[pedido["id"]]
        pedido["ventana"] = ventana_recogida(pedido)
    return pedidos


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
