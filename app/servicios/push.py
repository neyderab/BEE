"""Notificaciones push (Web Push): avisos al celular aunque la app esté cerrada.

Es gratis: usa el servicio de notificaciones que ya trae cada navegador
(Google, Apple, Mozilla). Solo se necesitan dos claves VAPID propias:

- En producción se guardan en VAPID_PUBLIC_KEY y VAPID_PRIVATE_KEY
  (créalas con: python scripts/generar_claves_push.py).
- En desarrollo, si no existen, se crean solas en .claves_push.json.
"""

import base64
import json
import logging
import os
import threading
from functools import lru_cache

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pywebpush import WebPushException, webpush

from app.config import RAIZ
from app.modelos import suscripciones_push

logger = logging.getLogger(__name__)

CLAVES_LOCALES = RAIZ / ".claves_push.json"
CORREO_CONTACTO = os.getenv("VAPID_CORREO", "mailto:admin@usebeeapp.com")
DURACION_SEGUNDOS = 6 * 60 * 60  # Si el celular está apagado, el aviso espera hasta 6 horas.


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


def crear_claves() -> dict:
    privada = ec.generate_private_key(ec.SECP256R1())
    publica = privada.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return {"publica": _b64(publica), "privada": _b64(privada.private_numbers().private_value.to_bytes(32, "big"))}


@lru_cache
def claves() -> dict:
    if os.getenv("VAPID_PUBLIC_KEY") and os.getenv("VAPID_PRIVATE_KEY"):
        return {"publica": os.environ["VAPID_PUBLIC_KEY"], "privada": os.environ["VAPID_PRIVATE_KEY"]}
    if CLAVES_LOCALES.exists():
        return json.loads(CLAVES_LOCALES.read_text())
    nuevas = crear_claves()
    CLAVES_LOCALES.write_text(json.dumps(nuevas))
    logger.warning("Se crearon claves push locales en %s. En producción usa VAPID_PUBLIC_KEY y VAPID_PRIVATE_KEY.", CLAVES_LOCALES)
    return nuevas


# ---------- Suscripciones ----------

def guardar_suscripcion(usuario_id: int, suscripcion: dict) -> bool:
    try:
        endpoint = suscripcion["endpoint"]
        p256dh, auth = suscripcion["keys"]["p256dh"], suscripcion["keys"]["auth"]
    except (KeyError, TypeError):
        return False
    if not (isinstance(endpoint, str) and endpoint.startswith("https://") and len(endpoint) < 1000):
        return False
    suscripciones_push.guardar(usuario_id, endpoint, p256dh, auth)
    return True


def borrar_suscripcion(endpoint: str, usuario_id: int | None = None) -> None:
    suscripciones_push.borrar(endpoint, usuario_id)


# ---------- Envío ----------

def enviar(usuario_id: int, texto: str, url: str = "/app") -> int:
    """Envía el aviso a todos los celulares del usuario. Devuelve cuántos lo recibieron."""
    datos = json.dumps({"titulo": "Bee", "cuerpo": texto, "url": url}, ensure_ascii=False)
    enviados = 0
    for s in suscripciones_push.de_usuario(usuario_id):
        try:
            webpush(
                subscription_info={"endpoint": s["endpoint"], "keys": {"p256dh": s["p256dh"], "auth": s["auth"]}},
                data=datos,
                vapid_private_key=claves()["privada"],
                vapid_claims={"sub": CORREO_CONTACTO},
                ttl=DURACION_SEGUNDOS,
                timeout=10,
            )
            enviados += 1
        except WebPushException as error:
            # 404/410: el usuario desinstaló la app o quitó el permiso.
            if error.response is not None and error.response.status_code in (404, 410):
                borrar_suscripcion(s["endpoint"])
            else:
                logger.warning("No se pudo enviar un aviso push: %s", error)
        except Exception as error:  # Sin internet, servicio caído, etc.: no debe afectar el pedido.
            logger.warning("No se pudo enviar un aviso push: %s", error)
    return enviados


def enviar_en_segundo_plano(usuario_id: int, texto: str, url: str = "/app") -> None:
    """Envía sin hacer esperar a quien cambió el pedido."""
    if os.getenv("PUSH_DESACTIVADO") == "1":
        return

    def tarea():
        try:
            enviar(usuario_id, texto, url)
        except Exception as error:
            logger.warning("Error enviando avisos push: %s", error)

    threading.Thread(target=tarea, daemon=True).start()
