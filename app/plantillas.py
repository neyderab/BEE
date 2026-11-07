"""Plantillas Jinja2 (escapan el HTML automáticamente) y mensajes flash."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app import permisos as P
from app.pedidos import ACCIONES, ESTADOS, PASOS, TIEMPOS, contar_sin_leer, texto_tiempo

CARPETA = Path(__file__).resolve().parent.parent / "templates"
ZONA_HORARIA = ZoneInfo("America/Bogota")

# Correo al que las tiendas escriben para cerrar su cuenta.
CORREO_SOPORTE = "admin@usebeeapp.com"

templates = Jinja2Templates(directory=CARPETA)


def pesos(valor: int) -> str:
    """12500 -> '$12.500'"""
    return "$" + f"{int(valor):,}".replace(",", ".")


def hora(momento: datetime) -> str:
    """Hora local de Colombia, por ejemplo '10:35'."""
    return momento.astimezone(ZONA_HORARIA).strftime("%H:%M")


def fecha_corta(momento: datetime) -> str:
    local = momento.astimezone(ZONA_HORARIA)
    if local.date() == datetime.now(ZONA_HORARIA).date():
        return f"hoy {local:%H:%M}"
    return local.strftime("%d/%m %H:%M")


def iniciales(nombre: str | None, apellido: str | None = "") -> str:
    letras = [p[0] for p in (nombre or "", apellido or "") if p]
    return "".join(letras).upper() or "?"


templates.env.filters.update(pesos=pesos, hora=hora, fecha_corta=fecha_corta)
templates.env.globals.update(
    ESTADOS=ESTADOS,
    ACCIONES=ACCIONES,
    PASOS=PASOS,
    TIEMPOS=TIEMPOS,
    texto_tiempo=texto_tiempo,
    iniciales=iniciales,
    CORREO_SOPORTE=CORREO_SOPORTE,
    P=P,
    tiene_permiso=P.tiene,
)


def mostrar_mensaje(request: Request, texto: str, tipo: str = "ok") -> None:
    """Guarda un mensaje para mostrarlo en la siguiente página."""
    request.session["mensaje"] = {"texto": texto, "tipo": tipo}


def render(request: Request, nombre: str, status_code: int = 200, **contexto):
    usuario = contexto.setdefault("usuario", getattr(request.state, "usuario", None))
    contexto["mensaje"] = request.session.pop("mensaje", None)
    if usuario:
        contexto["sin_leer"] = contar_sin_leer(usuario["id"])
    return templates.TemplateResponse(
        request, nombre, contexto, status_code=status_code
    )
