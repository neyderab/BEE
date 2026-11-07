"""Registro, inicio de sesión, verificación y perfil."""

from pathlib import Path

import psycopg
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.db import conectar, listar_universidades
from app.plantillas import CORREO_SOPORTE, render
from app.usuarios import insertar_usuario
from app.validacion import leer_universidad, telefono_valido, validar_texto
from app.sesion import (
    ESTUDIANTE,
    ROLES,
    TIENDA,
    cargar_usuario,
    pagina_inicio,
    perfil_completo,
    usuario_en_sesion,
)

router = APIRouter()

# Página de presentación (la misma que publica GitHub Pages desde docs/).
DOCS = Path(__file__).resolve().parent.parent.parent / "docs"
PRESENTACION = DOCS / "index.html"

# Código fijo de prueba mientras no exista el envío real por SMS.
CODIGO_PRUEBA = "123456"

# Teléfono que pidió el código. Se guarda en la sesión (firmada) y no en el
# formulario, para que nadie pueda cambiarlo y entrar a la cuenta de otro.
CLAVE_TELEFONO = "telefono_por_verificar"


@router.get("/")
def inicio(request: Request):
    """Con sesión, lleva al panel; sin sesión, muestra la página de presentación."""
    usuario_id = request.session.get("usuario_id")
    usuario = cargar_usuario(usuario_id) if usuario_id else None
    if usuario and usuario["activo"]:
        return RedirectResponse(pagina_inicio(usuario), 303)
    if PRESENTACION.exists():
        return FileResponse(PRESENTACION)
    return RedirectResponse("/login", 303)


# ---------- Registro ----------

@router.get("/registro")
def mostrar_registro(request: Request):
    return render(
        request,
        "registro.html",
        universidades=listar_universidades(),
        valores={"rol": ESTUDIANTE},
        errores={},
    )


@router.post("/registrar")
def registrar_usuario(
    request: Request,
    telefono: str = Form(""),
    nombre: str = Form(""),
    apellido: str = Form(""),
    rol: str = Form(""),
    universidad_id: str = Form(""),
    nombre_tienda: str = Form(""),
):
    valores = {
        "telefono": telefono.strip(),
        "nombre": nombre.strip(),
        "apellido": apellido.strip(),
        "rol": rol,
        "universidad_id": universidad_id,
        "nombre_tienda": nombre_tienda.strip(),
    }
    errores: dict[str, str] = {}

    if rol not in ROLES:
        errores["rol"] = "Elige si eres estudiante o tienda."
    universidad = leer_universidad(universidad_id, errores)
    validar_texto(valores["nombre"], "nombre", "tu nombre", 50, errores)
    validar_texto(valores["apellido"], "apellido", "tu apellido", 50, errores)
    if not telefono_valido(valores["telefono"]):
        errores["telefono"] = "El teléfono debe tener 10 dígitos."
    if rol == TIENDA:
        validar_texto(
            valores["nombre_tienda"], "nombre_tienda", "el nombre de la tienda", 80, errores
        )

    if not errores:
        try:
            with conectar() as conexion:
                insertar_usuario(
                    conexion,
                    valores["telefono"],
                    valores["nombre"],
                    valores["apellido"],
                    rol,
                    universidad,
                    valores["nombre_tienda"],
                )
        except psycopg.errors.UniqueViolation:
            errores["telefono"] = "Este teléfono ya está registrado. Inicia sesión."

    if errores:
        return render(
            request,
            "registro.html",
            status_code=400,
            universidades=listar_universidades(),
            valores=valores,
            errores=errores,
        )

    return render(request, "registro_exitoso.html", rol=rol)


# ---------- Inicio de sesión ----------

@router.get("/login")
def mostrar_login(request: Request):
    return render(request, "login.html")


@router.post("/login")
def iniciar_sesion(request: Request, telefono: str = Form("")):
    telefono = telefono.strip()
    if not telefono_valido(telefono):
        return render(
            request,
            "login.html",
            status_code=400,
            error="El teléfono debe tener 10 dígitos.",
            telefono=telefono,
        )

    with conectar() as conexion:
        usuario = conexion.execute(
            "SELECT id, activo FROM usuarios WHERE telefono = %s", (telefono,)
        ).fetchone()

    if usuario is None:
        return render(request, "cuenta_no_encontrada.html", status_code=404)
    if not usuario["activo"]:
        return render(
            request,
            "login.html",
            status_code=403,
            error=f"Esta cuenta está suspendida. Escríbenos a {CORREO_SOPORTE}.",
            telefono=telefono,
        )

    request.session[CLAVE_TELEFONO] = telefono
    return render(request, "verificar.html", telefono=telefono, codigo_prueba=CODIGO_PRUEBA)


@router.post("/verificar-codigo")
def verificar_codigo(request: Request, codigo: str = Form("")):
    telefono = request.session.get(CLAVE_TELEFONO)
    if not telefono:
        return RedirectResponse("/login", 303)

    if codigo.strip() != CODIGO_PRUEBA:
        return render(
            request,
            "verificar.html",
            status_code=400,
            telefono=telefono,
            codigo_prueba=CODIGO_PRUEBA,
            error="El código no es correcto. Vuelve a intentarlo.",
        )

    with conectar() as conexion:
        usuario = conexion.execute(
            "SELECT id FROM usuarios WHERE telefono = %s AND activo", (telefono,)
        ).fetchone()

    if usuario is None:
        request.session.pop(CLAVE_TELEFONO, None)
        return RedirectResponse("/login", 303)

    request.session.clear()
    request.session["usuario_id"] = usuario["id"]
    return RedirectResponse(pagina_inicio(cargar_usuario(usuario["id"])), 303)


@router.get("/logout")
def cerrar_sesion(request: Request):
    request.session.clear()
    return RedirectResponse("/login", 303)


# ---------- Completar perfil (cuentas creadas antes de las universidades) ----------

@router.get("/completar-perfil")
def mostrar_completar_perfil(request: Request, usuario: dict = Depends(usuario_en_sesion)):
    if perfil_completo(usuario):
        return RedirectResponse(pagina_inicio(usuario), 303)
    return render(
        request,
        "completar_perfil.html",
        universidades=listar_universidades(),
        valores={"universidad_id": str(usuario["universidad_id"] or "")},
        errores={},
    )


@router.post("/completar-perfil")
def completar_perfil(
    request: Request,
    universidad_id: str = Form(""),
    nombre_tienda: str = Form(""),
    usuario: dict = Depends(usuario_en_sesion),
):
    valores = {"universidad_id": universidad_id, "nombre_tienda": nombre_tienda.strip()}
    errores: dict[str, str] = {}
    universidad = leer_universidad(universidad_id, errores)
    necesita_tienda = usuario["rol"] == TIENDA and usuario["tienda_id"] is None
    if necesita_tienda:
        validar_texto(
            valores["nombre_tienda"], "nombre_tienda", "el nombre de la tienda", 80, errores
        )

    if errores:
        return render(
            request,
            "completar_perfil.html",
            status_code=400,
            universidades=listar_universidades(),
            valores=valores,
            errores=errores,
        )

    with conectar() as conexion:
        conexion.execute(
            "UPDATE usuarios SET universidad_id = %s WHERE id = %s",
            (universidad, usuario["id"]),
        )
        if necesita_tienda:
            conexion.execute(
                "INSERT INTO tiendas (usuario_id, nombre) VALUES (%s, %s)",
                (usuario["id"], valores["nombre_tienda"]),
            )

    return RedirectResponse(pagina_inicio(cargar_usuario(usuario["id"])), 303)
