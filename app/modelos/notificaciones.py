"""Notificaciones: la campana de la app y los avisos push al celular."""

from app.modelos.base_datos import ejecutar, todos, uno


def notificar(conexion, usuario_id: int | None, texto: str, pedido_id: int | None = None, url: str = "/app") -> None:
    """Crea la notificación dentro de la transacción de `conexion` y la envía al celular."""
    if usuario_id is None:  # El estudiante cerró su cuenta.
        return
    conexion.execute(
        "INSERT INTO notificaciones (usuario_id, pedido_id, texto) VALUES (%s, %s, %s)",
        (usuario_id, pedido_id, texto[:200]),
    )
    from app.servicios.push import enviar_en_segundo_plano  # Servicio externo: se carga al usarlo.

    enviar_en_segundo_plano(usuario_id, texto, url)


def recientes(usuario_id: int, limite: int = 15) -> list[dict]:
    return todos(
        "SELECT id, pedido_id, texto, leida, creada_en FROM notificaciones WHERE usuario_id = %s ORDER BY id DESC LIMIT %s",
        (usuario_id, limite),
    )


def contar_sin_leer(usuario_id: int) -> int:
    return uno("SELECT COUNT(*) AS n FROM notificaciones WHERE usuario_id = %s AND NOT leida", (usuario_id,))["n"]


def marcar_leidas(usuario_id: int) -> None:
    ejecutar("UPDATE notificaciones SET leida = TRUE WHERE usuario_id = %s AND NOT leida", (usuario_id,))
