"""Código de verificación por SMS con Twilio (mensajes normales, funciona en la cuenta de prueba).

Bee crea un código de 6 dígitos, guarda solo su HMAC en la base (app/modelos/codigos.py:
vence a los 10 minutos, máximo 5 intentos, un envío cada 30 segundos) y lo manda por SMS
con la API de mensajes de Twilio.

Se activa con tres variables de entorno (Render → Environment, o el .env):
    TWILIO_ACCOUNT_SID   Account SID de la consola de Twilio (empieza por AC)
    TWILIO_AUTH_TOKEN    Auth Token de la consola de Twilio
    TWILIO_NUMERO        Número de Twilio que envía los SMS, con +, por ejemplo +15551234567

Sin ellas, Bee sigue en modo de prueba: no envía nada y el código es 123456.

Cuenta de prueba (trial) de Twilio: solo deja enviar sus plantillas predefinidas. Con
TWILIO_CUENTA_DE_PRUEBA=1, Bee envía la plantilla de 2FA («sms_2fa»), que trae siempre
el código 482913, y acepta ese código. Sirve para demostrar el envío real de SMS, pero
NO es seguro para usuarios reales (el código no cambia): con una cuenta paga se quita.
"""

import hashlib
import hmac
import logging
import os
import secrets

import httpx

from app.config import CODIGO_PRUEBA, SECRET_KEY
from app.modelos import codigos

logger = logging.getLogger(__name__)

URL_MENSAJES = "https://api.twilio.com/2010-04-01/Accounts/{cuenta}/Messages.json"
PREFIJO_PAIS = "+57"  # Colombia: los teléfonos se guardan con 10 dígitos, sin el +57.
PLANTILLA_2FA = "sms_2fa"       # Plantilla de 2FA de la cuenta de prueba de Twilio...
CODIGO_PLANTILLA_2FA = "482913"  # ...que siempre envía este código.


class SMSNoDisponible(Exception):
    """No se pudo enviar el SMS; el mensaje es para mostrarle al usuario."""


def _credenciales() -> tuple[str, str, str] | None:
    datos = tuple(os.getenv(v, "").strip() for v in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_NUMERO"))
    return datos if all(datos) else None


def activo() -> bool:
    """True si hay credenciales de Twilio: el código llega por SMS. False: modo de prueba (123456)."""
    return _credenciales() is not None


def cuenta_de_prueba() -> bool:
    """True si Twilio es una cuenta de prueba: se envía la plantilla de 2FA con su código fijo."""
    return os.getenv("TWILIO_CUENTA_DE_PRUEBA", "").strip() == "1"


def _huella(telefono: str, codigo: str) -> str:
    """HMAC con SECRET_KEY: aunque alguien leyera la base, no podría sacar el código."""
    return hmac.new(SECRET_KEY.encode(), f"{telefono}:{codigo}".encode(), hashlib.sha256).hexdigest()


def enviar_codigo(telefono: str) -> str | None:
    """Crea un código nuevo y lo envía por SMS. Lanza SMSNoDisponible.

    Devuelve el código que hay que mostrar en pantalla, o None si llegó por SMS:
    - sin Twilio (modo de prueba): 123456;
    - cuenta de prueba de Twilio y el SMS no salió (número sin verificar u otro error):
      482913, el mismo código fijo de la plantilla, así cualquiera entra a la demostración.
    """
    if not activo():
        return CODIGO_PRUEBA
    if codigos.enviado_hace_poco(telefono):
        raise SMSNoDisponible("Ya te enviamos un código. Espera unos segundos antes de pedir otro.")
    if cuenta_de_prueba():
        codigo, texto = CODIGO_PLANTILLA_2FA, PLANTILLA_2FA
    else:
        codigo = f"{secrets.randbelow(10**6):06d}"
        texto = f"Tu código de Bee es {codigo}. Vence en {codigos.MINUTOS_VIGENCIA} minutos."
    codigos.guardar(telefono, _huella(telefono, codigo))
    cuenta, token, numero = _credenciales()
    try:
        respuesta = httpx.post(
            URL_MENSAJES.format(cuenta=cuenta),
            data={"To": PREFIJO_PAIS + telefono, "From": numero, "Body": texto},
            auth=(cuenta, token), timeout=10,
        )
    except httpx.HTTPError as error:
        logger.warning("Twilio no respondió: %s", error)
        if cuenta_de_prueba():
            return CODIGO_PLANTILLA_2FA  # Demostración: el código es fijo, se muestra en pantalla.
        codigos.borrar(telefono)
        raise SMSNoDisponible("No pudimos enviar el SMS. Intenta de nuevo en un momento.") from None
    if respuesta.status_code >= 400:
        # El detalle (sin credenciales) queda en el registro para quien administra Render.
        logger.warning("Twilio respondió %s: %s", respuesta.status_code, respuesta.text[:300])
        if cuenta_de_prueba():
            # Cuenta trial: el código es fijo y ya quedó guardado, así que si Twilio no
            # envía (número sin verificar, error 21608, u otro) se muestra en pantalla.
            return CODIGO_PLANTILLA_2FA
        codigos.borrar(telefono)
        raise SMSNoDisponible("No pudimos enviar el SMS a ese número. Revisa que esté bien escrito.")
    return None



def codigo_correcto(telefono: str, codigo: str) -> bool:
    """¿El código que escribió el usuario es el que le llegó por SMS?"""
    codigo = "".join(codigo.split())  # Acepta "482 913" o con espacios al copiar y pegar.
    if not (codigo.isdigit() and len(codigo) == 6):
        logger.warning("Código rechazado para …%s: no tiene 6 dígitos.", telefono[-4:])
        return False
    if not activo():
        return codigo == CODIGO_PRUEBA
    esperado = _huella(telefono, codigo)
    return codigos.comprobar(telefono, lambda guardado: hmac.compare_digest(guardado, esperado))
