"""Conexión a PostgreSQL y creación del esquema."""

import logging
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

ESQUEMA = Path(__file__).resolve().parent.parent / "schema.sql"


def conectar() -> psycopg.Connection:
    """Abre una conexión nueva. Las filas se devuelven como diccionarios.

    Usada con `with`, hace commit al salir sin errores y rollback si hay una
    excepción.
    """
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dbname=os.getenv("DB_NAME"),
        sslmode=os.getenv("DB_SSLMODE", "require"),
        row_factory=dict_row,
    )


def inicializar_db() -> None:
    """Crea las tablas que falten y agrega las universidades iniciales."""
    with conectar() as conexion:
        conexion.execute(ESQUEMA.read_text(encoding="utf-8"))

    # Va aparte: si la tabla original tiene teléfonos repetidos, el índice no
    # se puede crear, pero la aplicación debe seguir funcionando.
    try:
        with conectar() as conexion:
            conexion.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS usuarios_telefono_idx "
                "ON usuarios (telefono)"
            )
    except psycopg.errors.UniqueViolation:
        logger.warning(
            "Hay teléfonos repetidos en la tabla usuarios; "
            "no se pudo crear el índice único."
        )


def listar_universidades() -> list[dict]:
    with conectar() as conexion:
        return conexion.execute(
            "SELECT id, nombre, ciudad FROM universidades ORDER BY nombre"
        ).fetchall()


def universidad_existe(universidad_id: int) -> bool:
    with conectar() as conexion:
        fila = conexion.execute(
            "SELECT 1 FROM universidades WHERE id = %s", (universidad_id,)
        ).fetchone()
    return fila is not None
