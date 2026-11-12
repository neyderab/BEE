"""Crea el primer administrador de Bee (con todos los permisos y contraseña).

Los administradores no se pueden registrar desde la web: el primero se crea
con este script y después ese administrador crea a los demás desde /admin.

Uso:
    python scripts/crear_admin.py 3001234567 Nombre Apellido

El script pide la contraseña (no se ve mientras la escribes). Usa la misma
base de datos configurada en .env. Si el teléfono ya es de un administrador,
le pone la contraseña nueva y le devuelve todos los permisos (sirve para
recuperar el acceso).
"""

import getpass
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.modelos import permisos, usuarios  # noqa: E402  (después de ajustar sys.path)
from app.modelos.base_datos import aplicar_migraciones  # noqa: E402
from app.modelos.usuarios import ADMIN  # noqa: E402
from app.servicios import claves  # noqa: E402
from app.servicios.validacion import telefono_valido  # noqa: E402


def pedir_clave() -> str | None:
    clave = getpass.getpass(f"Contraseña del administrador (mínimo {claves.LARGO_MINIMO} caracteres): ")
    problema = claves.problema(clave, getpass.getpass("Repite la contraseña: "))
    if problema:
        print(problema)
        return None
    return clave


def main(argumentos: list[str], clave: str | None = None) -> int:
    """`clave` solo la pasan las pruebas; en la terminal se pide con getpass."""
    if len(argumentos) != 3:
        print(__doc__)
        return 1
    telefono, nombre, apellido = (a.strip() for a in argumentos)
    if not telefono_valido(telefono):
        print("El teléfono debe tener 10 dígitos, sin +57 ni espacios.")
        return 1
    if not nombre or not apellido:
        print("Escribe el nombre y el apellido.")
        return 1

    if clave is None:
        clave = pedir_clave()
        if clave is None:
            return 1
    elif claves.problema(clave):
        print(claves.problema(clave))
        return 1

    aplicar_migraciones()
    existente = usuarios.buscar_por_telefono(telefono)
    if existente and existente["rol"] != ADMIN:
        print(
            f"El teléfono {telefono} ya pertenece a una cuenta de tipo "
            f"«{existente['rol']}». Usa otro número para el administrador."
        )
        return 1
    if existente:
        usuarios.guardar_permisos(existente["id"], permisos.TODOS)
        usuarios.guardar_clave(existente["id"], claves.hashear(clave))
        usuarios.cambiar_activo(existente["id"], True)
        print(f"El administrador {telefono} ya existía: se reactivó con todos los permisos y la contraseña nueva.")
    else:
        usuarios.crear(telefono, nombre, apellido, ADMIN, None, permisos=permisos.TODOS, clave_hash=claves.hashear(clave))
        print(f"Administrador creado. Inicia sesión en /login con el teléfono {telefono}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
