"""Crea el primer administrador de BEE (con todos los permisos).

Los administradores no se pueden registrar desde la web: el primero se crea
con este script y después ese administrador crea a los demás desde /admin.

Uso:
    python crear_admin.py 3001234567 Nombre Apellido

Usa la misma base de datos configurada en .env. Si el teléfono ya es de un
administrador, le devuelve todos los permisos (sirve para recuperar el acceso).
"""

import sys

from dotenv import load_dotenv

load_dotenv()

from app import permisos  # noqa: E402
from app.db import conectar, inicializar_db  # noqa: E402
from app.sesion import ADMIN  # noqa: E402
from app.usuarios import guardar_permisos, insertar_usuario  # noqa: E402
from app.validacion import telefono_valido  # noqa: E402


def main(argumentos: list[str]) -> int:
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

    inicializar_db()
    with conectar() as conexion:
        existente = conexion.execute(
            "SELECT id, rol FROM usuarios WHERE telefono = %s", (telefono,)
        ).fetchone()
        if existente and existente["rol"] != ADMIN:
            print(
                f"El teléfono {telefono} ya pertenece a una cuenta de tipo "
                f"«{existente['rol']}». Usa otro número para el administrador."
            )
            return 1
        if existente:
            guardar_permisos(conexion, existente["id"], permisos.TODOS)
            conexion.execute("UPDATE usuarios SET activo = TRUE WHERE id = %s", (existente["id"],))
            print(f"El administrador {telefono} ya existía: se reactivó con todos los permisos.")
        else:
            insertar_usuario(conexion, telefono, nombre, apellido, ADMIN, None, permisos=permisos.TODOS)
            print(f"Administrador creado. Inicia sesión en /login con el teléfono {telefono}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
