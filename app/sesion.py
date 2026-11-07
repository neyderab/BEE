"""Usuario en sesión y control de acceso por rol."""

from fastapi import HTTPException, Request

from app.db import conectar

ESTUDIANTE = "Estudiante"
TIENDA = "Tienda"
ROLES = (ESTUDIANTE, TIENDA)


def redirigir(url: str) -> HTTPException:
    """Excepción que FastAPI convierte en una redirección."""
    return HTTPException(status_code=303, headers={"Location": url})


def cargar_usuario(usuario_id: int) -> dict | None:
    with conectar() as conexion:
        return conexion.execute(
            """
            SELECT u.id, u.telefono, u.nombre, u.apellido, u.rol,
                   u.universidad_id, un.nombre AS universidad,
                   t.id AS tienda_id, t.nombre AS tienda
            FROM usuarios u
            LEFT JOIN universidades un ON un.id = u.universidad_id
            LEFT JOIN tiendas t ON t.usuario_id = u.id
            WHERE u.id = %s
            """,
            (usuario_id,),
        ).fetchone()


def perfil_completo(usuario: dict) -> bool:
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
    return "/logout"  # Rol desconocido: evita un ciclo de redirecciones.


def usuario_en_sesion(request: Request) -> dict:
    """Dependencia: exige una sesión iniciada."""
    usuario_id = request.session.get("usuario_id")
    usuario = cargar_usuario(usuario_id) if usuario_id else None
    if usuario is None:
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
