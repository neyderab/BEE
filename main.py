import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()

from app.db import inicializar_db  # noqa: E402  (después de cargar .env)
from app.plantillas import render  # noqa: E402
from app.rutas import admin, auth, cuenta, estudiante, tienda  # noqa: E402
from app.sesion import SinPermiso  # noqa: E402

logger = logging.getLogger("bee")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = "solo-para-desarrollo-cambiar"
    logger.warning("SECRET_KEY no está definida en .env; usando una clave de desarrollo.")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    inicializar_db()
    yield


app = FastAPI(title="Bee", lifespan=ciclo_de_vida)
# En producción (HTTPS) define COOKIE_SEGURA=1 para que la cookie de sesión
# solo viaje cifrada.
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=os.getenv("COOKIE_SEGURA") == "1",
)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="static",
)

app.include_router(auth.router)
app.include_router(tienda.router)
app.include_router(estudiante.router)
app.include_router(cuenta.router)
app.include_router(admin.router)


@app.exception_handler(SinPermiso)
def sin_permiso(request: Request, _: SinPermiso):
    return render(
        request,
        "error.html",
        status_code=403,
        texto="No tienes permiso para ver esta página. Pídeselo a otro administrador.",
        volver="/admin",
    )


# La página de presentación (docs/) se sirve en la raíz: estilos, imágenes,
# PDF y diccionario de datos. Va al final para no tapar las rutas de la app.
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent / "docs"), name="presentacion")
