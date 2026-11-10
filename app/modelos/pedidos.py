"""Pedidos: estados, pagos, código de recogida y operaciones de estudiantes y tiendas.

Reglas principales:
- Un estudiante solo pide en tiendas de su universidad y si la tienda está abierta.
- La tienda avanza el pedido según TRANSICIONES; «entregado» solo se marca
  con el código de recogida que el estudiante muestra.
- Cada cambio genera una notificación (campana y aviso push).
"""

import secrets
from datetime import datetime, timedelta

from app.modelos.base_datos import conectar, todos, uno, campos_foto
from app.modelos.notificaciones import notificar
from app.modelos.tiendas import RANGO_MINUTOS, estado_tienda, texto_tiempo, tienda_abierta
from app.servicios.formato import pesos

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
CANTIDAD_MAXIMA = 20  # Unidades por producto en un pedido.

# Métodos de pago: (nombre, disponible). Por ahora solo se acepta efectivo.
METODOS_PAGO = {
    "efectivo": ("Efectivo", True),
    "nequi": ("Nequi", False),
    "debito": ("Tarjeta débito", False),
    "credito": ("Tarjeta crédito", False),
}
METODO_PREDETERMINADO = "efectivo"


class PedidoInvalido(Exception):
    """El pedido no se puede crear o cambiar; el mensaje explica por qué."""


def metodo_disponible(metodo: str) -> bool:
    return METODOS_PAGO.get(metodo, ("", False))[1]


def ventana_recogida(pedido: dict) -> tuple[datetime, datetime] | None:
    """Desde cuándo y hasta cuándo se puede recoger un pedido aceptado."""
    if pedido.get("aceptado_en") is None or pedido.get("tiempo_min") is None:
        return None
    inicio = pedido["aceptado_en"]
    return inicio + timedelta(minutes=pedido["tiempo_min"]), inicio + timedelta(minutes=pedido["tiempo_max"])


def mensaje_para_estudiante(
    estado: str, pedido_id: int, tienda: str, tiempo_min: int | None, codigo: str | None = None
) -> str:
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


# ---------- Consultas ----------

def agregar_items(pedidos: list[dict]) -> list[dict]:
    """Agrega a cada pedido sus productos (`items`) y su ventana de recogida."""
    if not pedidos:
        return pedidos
    ids = [p["id"] for p in pedidos]
    por_pedido: dict[int, list] = {i: [] for i in ids}
    for fila in todos(
        "SELECT pedido_id, nombre_producto, precio_unitario, cantidad FROM pedido_items WHERE pedido_id = ANY(%s) ORDER BY id",
        (ids,),
    ):
        por_pedido[fila["pedido_id"]].append(fila)
    for pedido in pedidos:
        pedido["items"] = por_pedido[pedido["id"]]
        pedido["ventana"] = ventana_recogida(pedido)
    return pedidos


def de_tienda(tienda_id: int) -> list[dict]:
    """Pedidos de una tienda con los datos del estudiante (sin el código de recogida)."""
    return agregar_items(todos(
        f"""
        SELECT p.id, p.estado, p.hora_recogida, p.total, p.creado_en, p.metodo_pago,
               p.tiempo_min, p.tiempo_max, p.aceptado_en, p.estudiante_id,
               u.nombre, u.apellido, u.telefono, {campos_foto("u")}
        FROM pedidos p
        LEFT JOIN usuarios u ON u.id = p.estudiante_id
        WHERE p.tienda_id = %s
        ORDER BY p.creado_en, p.id
        """,
        (tienda_id,),
    ))


def de_estudiante(estudiante_id: int, limite: int = 30) -> list[dict]:
    return agregar_items(todos(
        """
        SELECT p.id, p.estado, p.hora_recogida, p.total, p.creado_en, p.metodo_pago, p.tienda_id,
               p.tiempo_min, p.tiempo_max, p.aceptado_en, p.codigo_recogida, t.nombre AS tienda
        FROM pedidos p
        JOIN tiendas t ON t.id = p.tienda_id
        WHERE p.estudiante_id = %s
        ORDER BY p.creado_en DESC
        LIMIT %s
        """,
        (estudiante_id, limite),
    ))


def items_para_repetir(pedido_id: int, estudiante_id: int, tienda_id: int) -> list[dict]:
    """Productos de un pedido anterior del estudiante en esa tienda («Pedir de nuevo»)."""
    return todos(
        """
        SELECT i.producto_id, i.nombre_producto, i.cantidad FROM pedido_items i
        JOIN pedidos p ON p.id = i.pedido_id
        WHERE p.id = %s AND p.estudiante_id = %s AND p.tienda_id = %s
        """,
        (pedido_id, estudiante_id, tienda_id),
    )


def resumen_hoy() -> dict:
    return uno(
        """
        SELECT COUNT(*) FILTER (WHERE creado_en >= date_trunc('day', now())) AS hoy,
               COUNT(*) FILTER (WHERE estado = ANY(%s)) AS en_curso
        FROM pedidos
        """,
        (list(ACTIVOS),),
    )


def listar_todos(universidad_id: int | None = None, estado: str = "", limite: int = 100) -> list[dict]:
    """Pedidos de todas las tiendas, con filtros (para el administrador)."""
    condiciones, parametros = [], []
    if universidad_id:
        condiciones.append("dueno.universidad_id = %s")
        parametros.append(universidad_id)
    if estado in ESTADOS:
        condiciones.append("p.estado = %s")
        parametros.append(estado)
    donde = "WHERE " + " AND ".join(condiciones) if condiciones else ""
    return todos(
        f"""
        SELECT p.id, p.estado, p.total, p.creado_en, p.estudiante_id,
               t.nombre AS tienda, un.nombre AS universidad, e.nombre, e.apellido
        FROM pedidos p
        JOIN tiendas t ON t.id = p.tienda_id
        JOIN usuarios dueno ON dueno.id = t.usuario_id
        LEFT JOIN universidades un ON un.id = dueno.universidad_id
        LEFT JOIN usuarios e ON e.id = p.estudiante_id
        {donde}
        ORDER BY p.creado_en DESC
        LIMIT {int(limite)}
        """,
        parametros,
    )


# ---------- Operaciones del estudiante ----------

def crear(estudiante: dict, tienda: dict, cantidades: dict[int, int], metodo: str) -> dict:
    """Crea el pedido y avisa a la tienda. Devuelve {"id", "aceptado"}.

    Lanza PedidoInvalido si la tienda está cerrada, el pago no está disponible
    o algún producto no existe o está agotado.
    """
    if not tienda_abierta(tienda):
        raise PedidoInvalido(f"{tienda['nombre']} está cerrada. {estado_tienda(tienda)}.")
    if not metodo_disponible(metodo):
        raise PedidoInvalido("Por ahora solo puedes pagar en efectivo al recoger.")
    if not cantidades:
        raise PedidoInvalido("Agrega al menos un producto a tu pedido.")

    with conectar() as conexion:
        productos = conexion.execute(
            """
            SELECT p.id, p.nombre, p.precio FROM productos p JOIN menus m ON m.id = p.menu_id
            WHERE p.id = ANY(%s) AND m.tienda_id = %s AND p.disponible
            """,
            (list(cantidades), tienda["id"]),
        ).fetchall()
        if len(productos) != len(cantidades):
            raise PedidoInvalido("Algún producto ya no está disponible. Revisa tu pedido.")

        total = sum(p["precio"] * cantidades[p["id"]] for p in productos)
        # Se guarda el tiempo vigente: si la tienda lo cambia después, este
        # pedido conserva el que el estudiante vio al pedir.
        auto = tienda["auto_aceptar"]
        pedido_id = conexion.execute(
            """
            INSERT INTO pedidos (estudiante_id, tienda_id, total, tiempo_min, tiempo_max, estado, aceptado_en, metodo_pago)
            VALUES (%s, %s, %s, %s, %s, %s, CASE WHEN %s THEN now() END, %s)
            RETURNING id
            """,
            (estudiante["id"], tienda["id"], total, tienda["tiempo_min"], tienda["tiempo_min"] + RANGO_MINUTOS,
             "aceptado" if auto else "pendiente", auto, metodo),
        ).fetchone()["id"]
        with conexion.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO pedido_items (pedido_id, producto_id, nombre_producto, precio_unitario, cantidad) VALUES (%s, %s, %s, %s, %s)",
                [(pedido_id, p["id"], p["nombre"], p["precio"], cantidades[p["id"]]) for p in productos],
            )

        cliente = f"{estudiante['nombre']} {estudiante['apellido']}".strip()
        notificar(
            conexion, tienda["propietario_id"],
            f"Nuevo pedido #{pedido_id} de {cliente} por {pesos(total)}"
            + (" (aceptado automáticamente)." if auto else ". Acéptalo para empezar."),
            pedido_id, url="/tienda",
        )
        if auto:
            notificar(
                conexion, estudiante["id"],
                mensaje_para_estudiante("aceptado", pedido_id, tienda["nombre"], tienda["tiempo_min"]),
                pedido_id, url="/estudiante/pedidos",
            )
    return {"id": pedido_id, "aceptado": auto}


def cancelar_por_estudiante(estudiante: dict, pedido_id: int) -> bool:
    """Solo mientras la tienda no lo haya aceptado. Devuelve False si ya no se puede."""
    with conectar() as conexion:
        pedido = conexion.execute(
            """
            UPDATE pedidos p SET estado = 'cancelado' FROM tiendas t
            WHERE p.id = %s AND p.estudiante_id = %s AND p.estado = 'pendiente' AND t.id = p.tienda_id
            RETURNING p.id, t.usuario_id AS propietario_id
            """,
            (pedido_id, estudiante["id"]),
        ).fetchone()
        if pedido:
            cliente = f"{estudiante['nombre']} {estudiante['apellido']}".strip()
            notificar(conexion, pedido["propietario_id"], f"{cliente} canceló el pedido #{pedido_id}.", pedido_id, url="/tienda")
    return pedido is not None


# ---------- Operaciones de la tienda ----------

def cambiar_estado(tienda: dict, pedido_id: int, estado: str) -> None:
    """Avanza o cancela un pedido de la tienda y avisa al estudiante.

    `tienda` es el usuario de la tienda (con tienda_id y tienda). Al quedar
    listo se crea el código de recogida. Lanza PedidoInvalido si no se puede.
    """
    with conectar() as conexion:
        pedido = conexion.execute(
            "SELECT estado, estudiante_id, tiempo_min FROM pedidos WHERE id = %s AND tienda_id = %s FOR UPDATE",
            (pedido_id, tienda["tienda_id"]),
        ).fetchone()
        if pedido is None:
            raise PedidoInvalido("El pedido no existe.")
        if estado not in TRANSICIONES[pedido["estado"]]:
            raise PedidoInvalido("Ese cambio de estado no es posible.")
        codigo = generar_codigo(conexion, tienda["tienda_id"]) if estado == "listo" else None
        conexion.execute(
            """
            UPDATE pedidos
            SET estado = %s,
                aceptado_en = CASE WHEN %s = 'aceptado' THEN now() ELSE aceptado_en END,
                codigo_recogida = COALESCE(%s, codigo_recogida)
            WHERE id = %s
            """,
            (estado, estado, codigo, pedido_id),
        )
        notificar(
            conexion, pedido["estudiante_id"],
            mensaje_para_estudiante(estado, pedido_id, tienda["tienda"], pedido["tiempo_min"], codigo),
            pedido_id, url="/estudiante/pedidos",
        )


def entregar_con_codigo(tienda: dict, codigo: str) -> dict | None:
    """Entrega el pedido listo cuyo código dice el estudiante. None si no coincide."""
    codigo = codigo.strip()
    if not (codigo.isdigit() and len(codigo) == 4):
        return None
    with conectar() as conexion:
        pedido = conexion.execute(
            """
            UPDATE pedidos p SET estado = 'entregado'
            WHERE p.tienda_id = %s AND p.estado = 'listo' AND p.codigo_recogida = %s
            RETURNING p.id, p.estudiante_id, (SELECT nombre FROM usuarios WHERE id = p.estudiante_id) AS nombre
            """,
            (tienda["tienda_id"], codigo),
        ).fetchone()
        if pedido:
            notificar(
                conexion, pedido["estudiante_id"],
                mensaje_para_estudiante("entregado", pedido["id"], tienda["tienda"], None),
                pedido["id"], url="/estudiante/pedidos",
            )
    return pedido
