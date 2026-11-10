"""App instalable (PWA): manifest, service worker, inicio de la app e instalación."""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from app import push
from app.plantillas import render
from app.sesion import cargar_usuario, pagina_inicio, usuario_en_sesion

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


# ---------- Notificaciones push ----------

@router.get("/push/clave")
def clave_push():
    """Clave pública que el navegador necesita para activar los avisos."""
    return JSONResponse({"clave": push.claves()["publica"]})


@router.post("/push/suscribir")
async def suscribir_push(request: Request, usuario: dict = Depends(usuario_en_sesion)):
    try:
        suscripcion = await request.json()
    except ValueError:
        suscripcion = None
    if not push.guardar_suscripcion(usuario["id"], suscripcion):
        return JSONResponse({"ok": False}, status_code=400)
    return JSONResponse({"ok": True})


@router.post("/push/desuscribir")
async def desuscribir_push(request: Request, usuario: dict = Depends(usuario_en_sesion)):
    try:
        endpoint = (await request.json()).get("endpoint", "")
    except (ValueError, AttributeError):
        endpoint = ""
    push.borrar_suscripcion(endpoint, usuario["id"])
    return JSONResponse({"ok": True})
