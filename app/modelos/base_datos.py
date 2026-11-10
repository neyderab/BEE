"""Conexión a PostgreSQL, atajos de consulta y migraciones (Alembic)."""

import os

import psycopg
from psycopg.rows import dict_row

from app.config import MIGRACIONES


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

# Atajos para consultas de una sola sentencia (cada una en su propia
# transacción). Para varias sentencias que deben ir juntas, usa conectar().

def uno(sql: str, parametros=()) -> dict | None:
    with conectar() as conexion:
        return conexion.execute(sql, parametros).fetchone()

def todos(sql: str, parametros=()) -> list[dict]:
    with conectar() as conexion:
        return conexion.execute(sql, parametros).fetchall()

def ejecutar(sql: str, parametros=()) -> None:
    with conectar() as conexion:
        conexion.execute(sql, parametros)

def campos_foto(alias: str) -> str:
    """Columnas para mostrar la foto de perfil del usuario `alias` sin cargarla."""
    return (
        f"{alias}.foto IS NOT NULL AS tiene_foto, "
        f"COALESCE(EXTRACT(EPOCH FROM {alias}.foto_actualizada)::BIGINT, 0) AS foto_version"
    )

def aplicar_migraciones() -> None:
    """Aplica las migraciones pendientes (migraciones/versiones/)."""
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(MIGRACIONES)), "head")
