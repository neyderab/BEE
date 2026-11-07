"""Plantillas Jinja2 (escapan el HTML automáticamente) y mensajes flash."""

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

CARPETA = Path(__file__).resolve().parent.parent / "templates"

templates = Jinja2Templates(directory=CARPETA)


def pesos(valor: int) -> str:
    """12500 -> '$12.500'"""
    return "$" + f"{int(valor):,}".replace(",", ".")


templates.env.filters["pesos"] = pesos


def mostrar_mensaje(request: Request, texto: str, tipo: str = "ok") -> None:
    """Guarda un mensaje para mostrarlo en la siguiente página."""
    request.session["mensaje"] = {"texto": texto, "tipo": tipo}


def render(request: Request, nombre: str, status_code: int = 200, **contexto):
    contexto.setdefault("usuario", getattr(request.state, "usuario", None))
    contexto["mensaje"] = request.session.pop("mensaje", None)
    return templates.TemplateResponse(
        request, nombre, contexto, status_code=status_code
    )
