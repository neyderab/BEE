"""Configuración de pruebas.

Las pruebas BORRAN y recrean todas las tablas, así que solo se ejecutan contra
una base de datos de pruebas indicada explícitamente con TEST_DB_NAME:

    TEST_DB_HOST=localhost TEST_DB_USER=postgres TEST_DB_NAME=bee_test \
    TEST_DB_SSLMODE=disable pytest
"""

import os

import pytest

if not os.getenv("TEST_DB_NAME"):
    pytest.skip(
        "Define TEST_DB_NAME (y TEST_DB_HOST, TEST_DB_USER...) para correr las pruebas.",
        allow_module_level=True,
    )

for variable in ("HOST", "PORT", "USER", "PASSWORD", "NAME", "SSLMODE"):
    os.environ[f"DB_{variable}"] = os.getenv(f"TEST_DB_{variable}", "")
os.environ["DB_PORT"] = os.environ["DB_PORT"] or "5432"
os.environ["DB_SSLMODE"] = os.environ["DB_SSLMODE"] or "disable"
os.environ["SECRET_KEY"] = "clave-de-pruebas"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import conectar  # noqa: E402
from main import app  # noqa: E402

USB = "Universidad de San Buenaventura"
ANDES = "Universidad de los Andes"


@pytest.fixture(autouse=True)
def base_limpia():
    with conectar() as conexion:
        conexion.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")


@pytest.fixture
def cliente():
    with TestClient(app) as c:  # `with` ejecuta el arranque (crea las tablas)
        yield c


@pytest.fixture
def nuevo_cliente():
    """Permite tener varios usuarios con sesiones distintas a la vez."""
    clientes = []

    def crear():
        c = TestClient(app)
        c.__enter__()
        clientes.append(c)
        return c

    yield crear
    for c in clientes:
        c.__exit__(None, None, None)


def id_universidad(nombre: str) -> int:
    with conectar() as conexion:
        return conexion.execute(
            "SELECT id FROM universidades WHERE nombre = %s", (nombre,)
        ).fetchone()["id"]


def registrar(cliente, telefono, rol="Estudiante", universidad=USB, **extra):
    datos = {
        "telefono": telefono,
        "nombre": "Ana",
        "apellido": "Pérez",
        "rol": rol,
        "universidad_id": str(id_universidad(universidad)),
        **extra,
    }
    return cliente.post("/registrar", data=datos)


def entrar(cliente, telefono):
    cliente.post("/login", data={"telefono": telefono})
    return cliente.post("/verificar-codigo", data={"codigo": "123456"})
