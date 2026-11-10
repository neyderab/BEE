"""App instalable (PWA): manifest, service worker, inicio de la app e instalación."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.plantillas import render
from app.sesion import cargar_usuario, pagina_inicio

router = APIRouter()

PWA = Path(__file__).resolve().parent.parent.parent / "static" / "pwa"


@router.get("/app")
def inicio_app(request: Request):
    """La app instalada empieza aquí: sin sesión va a Iniciar sesión; con sesión, a su panel."""
    usuario_id = request.session.get("usuario_id")
    usuario = cargar_usuario(usuario_id) if usuario_id else None
    if usuario and usuario["activo"]:
        return RedirectResponse(pagina_inicio(usuario), 303)
    return RedirectResponse("/login", 303)


@router.get("/manifest.webmanifest")
def manifest():
    return FileResponse(PWA / "manifest.webmanifest", media_type="application/manifest+json")


@router.get("/sw.js")
def service_worker():
    # Va en la raíz para que controle toda la app; no se guarda en caché para
    # que las actualizaciones lleguen enseguida.
    return FileResponse(
        PWA / "sw.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"},
    )


@router.get("/instalar")
def instalar(request: Request):
    return render(request, "instalar.html", usuario=None)


@router.get("/offline")
def sin_conexion(request: Request):
    return render(request, "offline.html", usuario=None)
