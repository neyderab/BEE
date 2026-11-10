"""Universidades donde funciona Bee."""

import psycopg

from app.modelos.base_datos import ejecutar, todos, uno


def listar() -> list[dict]:
    return todos("SELECT id, nombre, ciudad FROM universidades ORDER BY nombre")


def existe(universidad_id: int) -> bool:
    return uno("SELECT 1 FROM universidades WHERE id = %s", (universidad_id,)) is not None


def listar_con_conteos() -> list[dict]:
    """Cada universidad con cuántos estudiantes y tiendas tiene (para el administrador)."""
    return todos(
        """
        SELECT un.id, un.nombre, un.ciudad,
               COUNT(u.id) FILTER (WHERE u.rol = 'Estudiante') AS estudiantes,
               COUNT(u.id) FILTER (WHERE u.rol = 'Tienda') AS tiendas
        FROM universidades un
        LEFT JOIN usuarios u ON u.universidad_id = un.id
        GROUP BY un.id
        ORDER BY un.nombre
        """
    )


def crear(nombre: str, ciudad: str) -> bool:
    """Devuelve False si ya existe una universidad con ese nombre."""
    try:
        ejecutar("INSERT INTO universidades (nombre, ciudad) VALUES (%s, %s)", (nombre, ciudad))
        return True
    except psycopg.errors.UniqueViolation:
        return False
