"""VISTA (la V de MVC): motor de plantillas Jinja2.

Prepara las plantillas de app/vistas/templates/ (filtros, funciones globales)
y ofrece `render`, que los controladores usan para responder con HTML.
Jinja2 escapa el HTML automáticamente, así el contenido de los usuarios no
puede inyectar código en la página.
"""

from datetime import datetime

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.config import CORREO_SOPORTE, ESTATICOS, PLANTILLAS, ZONA_HORARIA
from app.modelos import permisos as P
from app.modelos.notificaciones import contar_sin_leer
from app.modelos.pedidos import ACCIONES, ESTADOS, METODOS_PAGO, PASOS
from app.modelos.tiendas import TIEMPOS, estado_tienda, texto_tiempo, tienda_abierta
from app.servicios.csrf import campo_csrf, valor_csrf
from app.servicios.formato import pesos

templates = Jinja2Templates(directory=PLANTILLAS)


def estatico(archivo: str) -> str:
    """URL de un archivo de static/ con su versión (?v=...).

    La versión cambia cada vez que se modifica el archivo, así el navegador
    descarga los estilos nuevos en vez de usar los que guardó antes.
    """
    try:
        version = int((ESTATICOS / archivo).stat().st_mtime)
    except FileNotFoundError:
        version = 0
    return f"/static/{archivo}?v={version}"


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
    tienda_abierta=tienda_abierta,
    estado_tienda=estado_tienda,
    METODOS_PAGO=METODOS_PAGO,
    iniciales=iniciales,
    CORREO_SOPORTE=CORREO_SOPORTE,
    P=P,
    tiene_permiso=P.tiene,
    campo_csrf=campo_csrf,
    valor_csrf=valor_csrf,
    estatico=estatico,
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
