"""Permisos de los administradores.

Un administrador solo puede hacer lo que sus permisos le autorizan. Reglas
para evitar abusos:

- Nadie puede dar permisos que no tiene.
- Nadie puede cambiar sus propios permisos, suspenderse ni eliminarse.
- Cualquier acción sobre otro administrador (crearlo, editarlo, suspenderlo,
  eliminarlo) requiere "gestionar_permisos". Como quien actúa conserva ese
  permiso, siempre queda al menos un administrador capaz de gestionar a los
  demás.
"""

VER_USUARIOS = "ver_usuarios"
CREAR_USUARIOS = "crear_usuarios"
EDITAR_USUARIOS = "editar_usuarios"
ELIMINAR_USUARIOS = "eliminar_usuarios"
GESTIONAR_PERMISOS = "gestionar_permisos"
VER_PEDIDOS = "ver_pedidos"
GESTIONAR_UNIVERSIDADES = "gestionar_universidades"

# Nombre y descripción que se muestran al asignar permisos.
PERMISOS = {
    VER_USUARIOS: ("Ver usuarios", "Consultar la lista de usuarios y sus datos."),
    CREAR_USUARIOS: ("Crear usuarios", "Registrar estudiantes y tiendas."),
    EDITAR_USUARIOS: ("Editar usuarios", "Cambiar nombres y universidad, y suspender o reactivar cuentas."),
    ELIMINAR_USUARIOS: ("Eliminar usuarios", "Borrar cuentas de estudiantes y tiendas."),
    GESTIONAR_PERMISOS: (
        "Gestionar administradores",
        "Crear otros administradores y asignarles permisos.",
    ),
    VER_PEDIDOS: ("Ver pedidos", "Consultar los pedidos de todas las tiendas."),
    GESTIONAR_UNIVERSIDADES: ("Gestionar universidades", "Agregar universidades nuevas."),
}

TODOS = tuple(PERMISOS)


def tiene(usuario: dict | None, permiso: str) -> bool:
    return bool(usuario) and usuario.get("rol") == "Admin" and permiso in (usuario.get("permisos") or [])


def elegibles(actor: dict, elegidos) -> set[str]:
    """Permisos que `actor` puede dar: deben existir y él también debe tenerlos."""
    return set(elegidos) & set(TODOS) & set(actor["permisos"])


def combinar(actor: dict, actuales, elegidos) -> set[str]:
    """Nuevos permisos de otro administrador cuando `actor` los edita.

    Los permisos que `actor` no tiene no los puede tocar: se conservan tal como estaban.
    """
    return (set(actuales) - set(actor["permisos"])) | elegibles(actor, elegidos)
