"""Protección CSRF: cada formulario lleva un token secreto de la sesión.

Otra página web no conoce ese token, así que no puede enviar formularios a
Bee en nombre del usuario. Las plantillas lo agregan con {{ campo_csrf() }}
y main.py lo exige en todos los POST (dependencia global).
"""

import secrets

from fastapi import Request
from jinja2 import pass_context
from markupsafe import Markup

CAMPO = "csrf"
ENCABEZADO = "x-csrf-token"
METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS"}


class ErrorCSRF(Exception):
    """El formulario no trae el token correcto (main.py muestra el aviso)."""


def token_csrf(request: Request) -> str:
    token = request.session.get(CAMPO)
    if not token:
        token = request.session[CAMPO] = secrets.token_urlsafe(32)
    return token


@pass_context
def campo_csrf(contexto) -> Markup:
    return Markup('<input type="hidden" name="{}" value="{}">').format(CAMPO, token_csrf(contexto["request"]))


async def verificar_csrf(request: Request) -> None:
    """Dependencia global: exige el token en todo POST."""
    if request.method in METODOS_SEGUROS:
        return
    enviado = request.headers.get(ENCABEZADO)
    if not enviado:
        enviado = (await request.form()).get(CAMPO)
    esperado = request.session.get(CAMPO)
    if not (esperado and enviado and secrets.compare_digest(str(enviado), esperado)):
        raise ErrorCSRF()


@pass_context
def valor_csrf(contexto) -> str:
    """El token, para pedidos hechos con JavaScript (encabezado X-CSRF-Token)."""
    return token_csrf(contexto["request"])
