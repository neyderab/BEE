"""Dependencias de FastAPI: usuario en sesión, roles y permisos.

Los controladores las piden con Depends(...). Si el usuario no tiene acceso,
se le redirige (sin sesión → /login; otro rol → su propio panel) o se
muestra «No tienes permiso».
"""

from fastapi import HTTPException, Request

from app.modelos import usuarios
from app.modelos.usuarios import ADMIN, ESTUDIANTE, TIENDA


class SinPermiso(Exception):
    """El usuario no tiene permiso para ver esta página (main.py la muestra)."""


def redirigir(url: str) -> HTTPException:
    """Excepción que FastAPI convierte en una redirección."""
    return HTTPException(status_code=303, headers={"Location": url})


def pagina_inicio(usuario: dict) -> str:
    """A dónde va cada usuario al entrar."""
    if not usuarios.perfil_completo(usuario):
        return "/completar-perfil"
    return {TIENDA: "/tienda", ESTUDIANTE: "/estudiante", ADMIN: "/admin"}.get(
        usuario["rol"], "/logout"  # Rol desconocido: evita un ciclo de redirecciones.
    )


def usuario_actual(request: Request) -> dict | None:
    """El usuario de la sesión, o None si no hay sesión o la cuenta está suspendida."""
    usuario_id = request.session.get("usuario_id")
    usuario = usuarios.cargar(usuario_id) if usuario_id else None
    return usuario if usuario and usuario["activo"] else None


def usuario_en_sesion(request: Request) -> dict:
    """Dependencia: exige una sesión iniciada."""
    usuario = usuario_actual(request)
    if usuario is None:
        # Solo se quita el usuario: borrar toda la sesión eliminaría también el token
        # CSRF y el inicio de sesión que esté en curso en otra pestaña («La página venció»).
        request.session.pop("usuario_id", None)
        raise redirigir("/login")
    request.state.usuario = usuario
    return usuario


def _exigir_rol(request: Request, rol: str) -> dict:
    usuario = usuario_en_sesion(request)
    if usuario["rol"] != rol or not usuarios.perfil_completo(usuario):
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
