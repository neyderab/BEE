"""Código de verificación por SMS con Twilio Verify.

Twilio genera el código de 6 dígitos, lo envía por SMS, controla que venza a
los 10 minutos y limita los intentos. Bee solo le pide «envía» y «revisa».

Se activa con tres variables de entorno (Render → Environment, o el .env):
    TWILIO_ACCOUNT_SID          Account SID de la consola de Twilio (empieza por AC)
    TWILIO_AUTH_TOKEN           Auth Token de la consola de Twilio
    TWILIO_VERIFY_SERVICE_SID   SID del servicio de Verify (empieza por VA)

Sin ellas, Bee sigue en modo de prueba: no envía nada y el código es 123456.
"""

import logging
import os

import httpx

from app.config import CODIGO_PRUEBA

logger = logging.getLogger(__name__)

URL_VERIFY = "https://verify.twilio.com/v2/Services/{servicio}/{accion}"
PREFIJO_PAIS = "+57"  # Colombia: los teléfonos se guardan con 10 dígitos, sin el +57.


class SMSNoDisponible(Exception):
    """Twilio no respondió o rechazó el envío; el mensaje es para mostrarle al usuario."""


def _credenciales() -> tuple[str, str, str] | None:
    datos = (
        os.getenv("TWILIO_ACCOUNT_SID", "").strip(),
        os.getenv("TWILIO_AUTH_TOKEN", "").strip(),
        os.getenv("TWILIO_VERIFY_SERVICE_SID", "").strip(),
    )
    return datos if all(datos) else None


def activo() -> bool:
    """True si hay credenciales de Twilio: el código llega por SMS. False: modo de prueba (123456)."""
    return _credenciales() is not None


def _llamar(accion: str, datos: dict) -> dict:
    cuenta, token, servicio = _credenciales()
    try:
        respuesta = httpx.post(
            URL_VERIFY.format(servicio=servicio, accion=accion), data=datos, auth=(cuenta, token), timeout=10
        )
    except httpx.HTTPError as error:
        logger.warning("Twilio no respondió: %s", error)
        raise SMSNoDisponible("No pudimos enviar el SMS. Intenta de nuevo en un momento.") from None
    if respuesta.status_code == 429:
        raise SMSNoDisponible("Pediste demasiados códigos. Espera unos minutos e intenta de nuevo.")
    if respuesta.status_code >= 400:
        # El detalle (sin credenciales) queda en el registro para quien administra Render.
        logger.warning("Twilio respondió %s en %s: %s", respuesta.status_code, accion, respuesta.text[:300])
        if accion == "VerificationCheck" and respuesta.status_code == 404:
            return {"status": "expired"}  # El código venció o ya se usó.
        raise SMSNoDisponible("No pudimos enviar el SMS a ese número. Revisa que esté bien escrito.")
    return respuesta.json()


def enviar_codigo(telefono: str) -> None:
    """Envía el código por SMS. En modo de prueba no hace nada. Lanza SMSNoDisponible."""
    if activo():
        _llamar("Verifications", {"To": PREFIJO_PAIS + telefono, "Channel": "sms", "Locale": "es"})


def codigo_correcto(telefono: str, codigo: str) -> bool:
    """¿El código que escribió el usuario es el que le llegó? Lanza SMSNoDisponible si Twilio falla."""
    codigo = codigo.strip()
    if not (codigo.isdigit() and 4 <= len(codigo) <= 10):
        return False
    if not activo():
        return codigo == CODIGO_PRUEBA
    return _llamar("VerificationCheck", {"To": PREFIJO_PAIS + telefono, "Code": codigo}).get("status") == "approved"
