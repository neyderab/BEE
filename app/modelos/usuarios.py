"""Usuarios: estudiantes, tiendas y administradores."""

import psycopg

from app.modelos.base_datos import campos_foto, conectar, ejecutar, todos, uno
from app.modelos.pedidos import ACTIVOS

ESTUDIANTE = "Estudiante"
TIENDA = "Tienda"
ADMIN = "Admin"
# Roles que cualquiera puede elegir al registrarse. Los administradores solo
# los crea otro administrador.
ROLES = (ESTUDIANTE, TIENDA)
TODOS_LOS_ROLES = (ESTUDIANTE, TIENDA, ADMIN)


class TelefonoRepetido(Exception):
    """Ya existe un usuario con ese teléfono."""


# ---------- Consultas ----------

def cargar(usuario_id: int) -> dict | None:
    """El usuario con su universidad, su tienda (si tiene) y sus permisos."""
    return uno(
        f"""
        SELECT u.id, u.telefono, u.nombre, u.apellido, u.rol, u.activo,
               u.universidad_id, un.nombre AS universidad, {campos_foto("u")},
               t.id AS tienda_id, t.nombre AS tienda, t.tiempo_min, t.auto_aceptar,
               t.abierta, t.hora_apertura, t.hora_cierre,
               ARRAY(SELECT permiso FROM permisos_usuario WHERE usuario_id = u.id ORDER BY permiso) AS permisos
        FROM usuarios u
        LEFT JOIN universidades un ON un.id = u.universidad_id
        LEFT JOIN tiendas t ON t.usuario_id = u.id
        WHERE u.id = %s
        """,
        (usuario_id,),
    )


def buscar_por_telefono(telefono: str) -> dict | None:
    return uno("SELECT id, rol, activo FROM usuarios WHERE telefono = %s", (telefono,))


def perfil_completo(usuario: dict) -> bool:
    """Estudiantes y tiendas necesitan universidad; las tiendas, además, su tienda."""
    if usuario["rol"] == ADMIN:
        return True  # Los administradores no pertenecen a una universidad.
    if usuario["universidad_id"] is None:
        return False
    return not (usuario["rol"] == TIENDA and usuario["tienda_id"] is None)


def listar(q: str = "", rol: str = "", estado: str = "", limite: int = 200) -> list[dict]:
    """Búsqueda del administrador por nombre, teléfono o tienda; filtros por rol y estado."""
    condiciones, parametros = [], []
    if q.strip():
        patron = f"%{q.strip()}%"
        condiciones.append("(u.nombre || ' ' || u.apellido ILIKE %s OR u.telefono LIKE %s OR t.nombre ILIKE %s)")
        parametros += [patron, patron, patron]
    if rol in TODOS_LOS_ROLES:
        condiciones.append("u.rol = %s")
        parametros.append(rol)
    if estado in ("activo", "suspendido"):
        condiciones.append("u.activo" if estado == "activo" else "NOT u.activo")
    donde = "WHERE " + " AND ".join(condiciones) if condiciones else ""
    return todos(
        f"""
        SELECT u.id, u.nombre, u.apellido, u.telefono, u.rol, u.activo, u.creado_en,
               un.nombre AS universidad, t.nombre AS tienda, {campos_foto("u")}
        FROM usuarios u
        LEFT JOIN universidades un ON un.id = u.universidad_id
        LEFT JOIN tiendas t ON t.usuario_id = u.id
        {donde}
        ORDER BY u.creado_en DESC, u.id DESC
        LIMIT {int(limite)}
        """,
        parametros,
    )


def contar_por_rol() -> dict[str, int]:
    return {f["rol"]: f["n"] for f in todos("SELECT rol, COUNT(*) AS n FROM usuarios GROUP BY rol")}


def pedidos_en_curso(usuario: dict) -> int:
    """Pedidos sin terminar del estudiante o de su tienda."""
    return uno(
        "SELECT COUNT(*) AS n FROM pedidos WHERE (estudiante_id = %s OR tienda_id = %s) AND estado = ANY(%s)",
        (usuario["id"], usuario.get("tienda_id"), list(ACTIVOS)),
    )["n"]


def resumen_pedidos(usuario: dict) -> dict:
    return uno(
        """
        SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE estado = ANY(%s)) AS en_curso
        FROM pedidos WHERE estudiante_id = %s OR tienda_id = %s
        """,
        (list(ACTIVOS), usuario["id"], usuario.get("tienda_id")),
    )


def foto(usuario_id: int) -> dict | None:
    return uno("SELECT foto FROM usuarios WHERE id = %s AND foto IS NOT NULL", (usuario_id,))


# ---------- Cambios ----------

def crear(
    telefono: str,
    nombre: str,
    apellido: str,
    rol: str,
    universidad_id: int | None,
    nombre_tienda: str = "",
    permisos=(),
    clave_hash: str | None = None,
) -> int:
    """Crea el usuario (y su tienda o sus permisos) en una sola transacción. Devuelve su id."""
    try:
        with conectar() as conexion:
            usuario_id = conexion.execute(
                """
                INSERT INTO usuarios (telefono, nombre, apellido, rol, universidad_id, clave_hash)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (telefono, nombre, apellido, rol, universidad_id, clave_hash),
            ).fetchone()["id"]
            if rol == TIENDA:
                conexion.execute("INSERT INTO tiendas (usuario_id, nombre) VALUES (%s, %s)", (usuario_id, nombre_tienda))
            _guardar_permisos(conexion, usuario_id, permisos)
    except psycopg.errors.UniqueViolation as error:
        raise TelefonoRepetido(telefono) from error
    return usuario_id


def guardar_permisos(usuario_id: int, permisos) -> None:
    with conectar() as conexion:
        _guardar_permisos(conexion, usuario_id, permisos)


def _guardar_permisos(conexion, usuario_id: int, permisos) -> None:
    """Reemplaza los permisos del usuario por `permisos`."""
    conexion.execute("DELETE FROM permisos_usuario WHERE usuario_id = %s", (usuario_id,))
    with conexion.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO permisos_usuario (usuario_id, permiso) VALUES (%s, %s)",
            [(usuario_id, p) for p in sorted(set(permisos))],
        )


def actualizar_datos(usuario: dict, nombre: str, apellido: str, universidad_id=None, nombre_tienda=None) -> None:
    """Cambia nombre y apellido; opcionalmente la universidad y el nombre de su tienda."""
    with conectar() as conexion:
        conexion.execute(
            "UPDATE usuarios SET nombre = %s, apellido = %s, universidad_id = COALESCE(%s, universidad_id) WHERE id = %s",
            (nombre, apellido, universidad_id, usuario["id"]),
        )
        if nombre_tienda is not None and usuario.get("tienda_id"):
            conexion.execute("UPDATE tiendas SET nombre = %s WHERE id = %s", (nombre_tienda, usuario["tienda_id"]))


def completar_perfil(usuario: dict, universidad_id: int, nombre_tienda: str | None) -> None:
    """Para cuentas creadas antes de las universidades: asigna universidad y crea su tienda."""
    with conectar() as conexion:
        conexion.execute("UPDATE usuarios SET universidad_id = %s WHERE id = %s", (universidad_id, usuario["id"]))
        if nombre_tienda is not None:
            conexion.execute("INSERT INTO tiendas (usuario_id, nombre) VALUES (%s, %s)", (usuario["id"], nombre_tienda))


def leer_clave_hash(usuario_id: int) -> str | None:
    """El hash de la contraseña del administrador (no se incluye en cargar() a propósito)."""
    fila = uno("SELECT clave_hash FROM usuarios WHERE id = %s", (usuario_id,))
    return fila["clave_hash"] if fila else None


def guardar_clave(usuario_id: int, clave_hash: str) -> None:
    ejecutar("UPDATE usuarios SET clave_hash = %s WHERE id = %s", (clave_hash, usuario_id))


def cambiar_activo(usuario_id: int, activo: bool) -> None:
    ejecutar("UPDATE usuarios SET activo = %s WHERE id = %s", (activo, usuario_id))


def guardar_foto(usuario_id: int, jpeg: bytes | None) -> None:
    """Guarda la foto de perfil, o la quita si `jpeg` es None."""
    if jpeg is None:
        ejecutar("UPDATE usuarios SET foto = NULL, foto_actualizada = NULL WHERE id = %s", (usuario_id,))
    else:
        ejecutar("UPDATE usuarios SET foto = %s, foto_actualizada = now() WHERE id = %s", (jpeg, usuario_id))


def eliminar(usuario_id: int) -> None:
    """Borra al usuario. Si era estudiante, sus pedidos pasados quedan sin sus datos."""
    ejecutar("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
