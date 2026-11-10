"""Celulares y navegadores que reciben avisos push de cada usuario."""

from app.modelos.base_datos import ejecutar, todos


def guardar(usuario_id: int, endpoint: str, p256dh: str, auth: str) -> None:
    ejecutar(
        """
        INSERT INTO suscripciones_push (usuario_id, endpoint, p256dh, auth) VALUES (%s, %s, %s, %s)
        ON CONFLICT (endpoint) DO UPDATE SET usuario_id = EXCLUDED.usuario_id,
            p256dh = EXCLUDED.p256dh, auth = EXCLUDED.auth
        """,
        (usuario_id, endpoint, p256dh, auth),
    )


def borrar(endpoint: str, usuario_id: int | None = None) -> None:
    if usuario_id is None:
        ejecutar("DELETE FROM suscripciones_push WHERE endpoint = %s", (endpoint,))
    else:
        ejecutar("DELETE FROM suscripciones_push WHERE endpoint = %s AND usuario_id = %s", (endpoint, usuario_id))


def de_usuario(usuario_id: int) -> list[dict]:
    return todos("SELECT endpoint, p256dh, auth FROM suscripciones_push WHERE usuario_id = %s", (usuario_id,))
