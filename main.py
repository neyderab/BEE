"""Punto de entrada de Bee: arma la aplicación FastAPI con sus capas MVC.

    Modelo        app/modelos/        datos y reglas de negocio (SQL)
    Vista         app/vistas/         plantillas HTML, CSS y JavaScript
    Controlador   app/controladores/  rutas HTTP
    Servicios     app/servicios/      CSRF, fotos, avisos push, validación

Inicia la app con:  python3 main.py   (ver ARQUITECTURA.md)
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import COOKIE_SEGURA, ESTATICOS, PRESENTACION, SECRET_KEY, SECRET_KEY_DE_DESARROLLO
from app.controladores import admin, auth, cuenta, estudiante, pwa, tienda
from app.controladores.dependencias import SinPermiso
from app.modelos import pedidos
from app.modelos.base_datos import aplicar_migraciones
from app.servicios.csrf import ErrorCSRF, verificar_csrf
from app.vistas.plantillas import render

if SECRET_KEY_DE_DESARROLLO:
    logging.getLogger("bee").warning("SECRET_KEY no está definida en .env; usando una clave de desarrollo.")


async def revisar_pedidos_vencidos():
    """Cada minuto cancela los pedidos aceptados que no avanzaron (ver pedidos.cancelar_vencidos)."""
    while True:
        await asyncio.sleep(60)
        try:
            await asyncio.to_thread(pedidos.cancelar_vencidos)
        except Exception:  # Un fallo pasajero de la base no debe detener la revisión.
            logging.getLogger("bee").exception("No se pudieron revisar los pedidos vencidos.")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    aplicar_migraciones()  # Pone la base de datos al día antes de atender pedidos.
    revision = asyncio.create_task(revisar_pedidos_vencidos())
    yield
    revision.cancel()
    with suppress(asyncio.CancelledError):
        await revision


# Todo POST exige el token CSRF (app/servicios/csrf.py).
app = FastAPI(title="Bee", lifespan=ciclo_de_vida, dependencies=[Depends(verificar_csrf)])

# Sesión en una cookie firmada. En producción (HTTPS) COOKIE_SEGURA=1.
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, same_site="lax", https_only=COOKIE_SEGURA)

# ---------- Controladores ----------
for controlador in (auth, estudiante, tienda, cuenta, admin, pwa):
    app.include_router(controlador.router)


@app.exception_handler(ErrorCSRF)
def csrf_invalido(request: Request, _: ErrorCSRF):
    return render(request, "errores/expirada.html", status_code=403, usuario=None)


@app.exception_handler(SinPermiso)
def sin_permiso(request: Request, _: SinPermiso):
    return render(
        request, "errores/error.html", status_code=403,
        texto="No tienes permiso para ver esta página. Pídeselo a otro administrador.", volver="/admin",
    )


# ---------- Archivos de la vista y página de presentación ----------
app.mount("/static", StaticFiles(directory=ESTATICOS), name="static")
# docs/ (la misma página que publica GitHub Pages) se sirve en la raíz.
# Va al final para no tapar las rutas de los controladores.
app.mount("/", StaticFiles(directory=PRESENTACION), name="presentacion")


if __name__ == "__main__":
    import uvicorn

    print("Bee está corriendo en http://127.0.0.1:8000  (Ctrl+C para detener)")
    uvicorn.run("main:app", host="127.0.0.1", port=int(os.getenv("PORT", "8000")), reload=True)
