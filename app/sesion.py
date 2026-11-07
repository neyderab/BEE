"""Usuario en sesión y control de acceso por rol."""

from fastapi import HTTPException, Request

from app.db import campos_foto, uno

ESTUDIANTE = "Estudiante"
TIENDA = "Tienda"
ADMIN = "Admin"
# Roles que cualquiera puede elegir al registrarse. Los administradores solo
# los crea otro administrador.
ROLES = (ESTUDIANTE, TIENDA)
TODOS_LOS_ROLES = (ESTUDIANTE, TIENDA, ADMIN)


class SinPermiso(Exception):
    """El usuario no tiene permiso para ver esta página (main.py la muestra)."""


def redirigir(url: str) -> HTTPException:
    """Excepción que FastAPI convierte en una redirección."""
    return HTTPException(status_code=303, headers={"Location": url})


def cargar_usuario(usuario_id: int) -> dict | None:
    return uno(
        f"""
        SELECT u.id, u.telefono, u.nombre, u.apellido, u.rol, u.activo,
               u.universidad_id, un.nombre AS universidad, {campos_foto("u")},
               t.id AS tienda_id, t.nombre AS tienda, t.tiempo_min, t.auto_aceptar,
               ARRAY(SELECT permiso FROM permisos_usuario WHERE usuario_id = u.id ORDER BY permiso) AS permisos
        FROM usuarios u
        LEFT JOIN universidades un ON un.id = u.universidad_id
        LEFT JOIN tiendas t ON t.usuario_id = u.id
        WHERE u.id = %s
        """,
        (usuario_id,),
    )


def perfil_completo(usuario: dict) -> bool:
    if usuario["rol"] == ADMIN:
        return True  # Los administradores no pertenecen a una universidad.
    if usuario["universidad_id"] is None:
        return False
    if usuario["rol"] == TIENDA and usuario["tienda_id"] is None:
        return False
    return True


def pagina_inicio(usuario: dict) -> str:
    if not perfil_completo(usuario):
        return "/completar-perfil"
    if usuario["rol"] == TIENDA:
        return "/tienda"
    if usuario["rol"] == ESTUDIANTE:
        return "/estudiante"
    if usuario["rol"] == ADMIN:
        return "/admin"
    return "/logout"  # Rol desconocido: evita un ciclo de redirecciones.


def usuario_en_sesion(request: Request) -> dict:
    """Dependencia: exige una sesión iniciada."""
    usuario_id = request.session.get("usuario_id")
    usuario = cargar_usuario(usuario_id) if usuario_id else None
    if usuario is None or not usuario["activo"]:
        request.session.clear()
        raise redirigir("/login")
    request.state.usuario = usuario
    return usuario


def _exigir_rol(request: Request, rol: str) -> dict:
    usuario = usuario_en_sesion(request)
    if usuario["rol"] != rol or not perfil_completo(usuario):
        raise redirigir(pagina_inicio(usuario))
    return usuario


def estudiante_en_sesion(request: Request) -> dict:
    return _exigir_rol(request, ESTUDIANTE)


def tienda_en_sesion(request: Request) -> dict:
    return _exigir_rol(request, TIENDA)


def admin_en_sesion(request: Request) -> dict:
    return _exigir_rol(request, ADMIN)


def requiere_permiso(permiso: str):
    """Dependencia: exige un administrador con `permiso`."""

    def dependencia(request: Request) -> dict:
        usuario = admin_en_sesion(request)
        if permiso not in usuario["permisos"]:
            raise SinPermiso()
        return usuario

    return dependencia
