"""Creación de usuarios (la usan el registro público y el administrador)."""

from app.sesion import TIENDA


def insertar_usuario(
    conexion,
    telefono: str,
    nombre: str,
    apellido: str,
    rol: str,
    universidad_id: int | None,
    nombre_tienda: str = "",
    permisos: list[str] | tuple = (),
) -> int:
    """Crea el usuario (y su tienda o sus permisos). Devuelve su id.

    Lanza psycopg.errors.UniqueViolation si el teléfono ya existe.
    """
    usuario_id = conexion.execute(
        """
        INSERT INTO usuarios (telefono, nombre, apellido, rol, universidad_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (telefono, nombre, apellido, rol, universidad_id),
    ).fetchone()["id"]
    if rol == TIENDA:
        conexion.execute(
            "INSERT INTO tiendas (usuario_id, nombre) VALUES (%s, %s)",
            (usuario_id, nombre_tienda),
        )
    guardar_permisos(conexion, usuario_id, permisos)
    return usuario_id


def guardar_permisos(conexion, usuario_id: int, permisos) -> None:
    """Reemplaza los permisos del usuario por `permisos`."""
    conexion.execute("DELETE FROM permisos_usuario WHERE usuario_id = %s", (usuario_id,))
    with conexion.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO permisos_usuario (usuario_id, permiso) VALUES (%s, %s)",
            [(usuario_id, p) for p in sorted(set(permisos))],
        )
