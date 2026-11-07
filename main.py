import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()

from app.db import inicializar_db  # noqa: E402  (después de cargar .env)
from app.rutas import auth, cuenta, estudiante, tienda  # noqa: E402

logger = logging.getLogger("bee")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = "solo-para-desarrollo-cambiar"
    logger.warning("SECRET_KEY no está definida en .env; usando una clave de desarrollo.")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    inicializar_db()
    yield


app = FastAPI(title="BEE", lifespan=ciclo_de_vida)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, same_site="lax")
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="static",
)

app.include_router(auth.router)
app.include_router(tienda.router)
app.include_router(estudiante.router)
app.include_router(cuenta.router)
