"""Controlador de acceso: portada, registro, inicio de sesión, verificación y perfil."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.config import CODIGO_PRUEBA, CORREO_SOPORTE, PRESENTACION
from app.controladores.dependencias import pagina_inicio, usuario_actual, usuario_en_sesion
from app.modelos import universidades, usuarios
from app.modelos.usuarios import ESTUDIANTE, ROLES, TIENDA
from app.servicios.validacion import Formulario, telefono_valido
from app.vistas.plantillas import render

router = APIRouter()

# Teléfono que pidió el código. Se guarda en la sesión (firmada) y no en el
# formulario, para que nadie pueda cambiarlo y entrar a la cuenta de otro.
CLAVE_TELEFONO = "telefono_por_verificar"


@router.get("/")
def inicio(request: Request):
    """Con sesión, lleva al panel; sin sesión, muestra la página de presentación."""
    usuario = usuario_actual(request)
    if usuario:
        return RedirectResponse(pagina_inicio(usuario), 303)
    portada = PRESENTACION / "index.html"
    return FileResponse(portada) if portada.exists() else RedirectResponse("/login", 303)


# ---------- Registro ----------

@router.get("/registro")
def mostrar_registro(request: Request):
    return render(
        request, "auth/registro.html", universidades=universidades.listar(), valores={"rol": ESTUDIANTE}, errores={}
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
    f = Formulario(
        telefono=telefono, nombre=nombre, apellido=apellido, rol=rol,
        universidad_id=universidad_id, nombre_tienda=nombre_tienda,
    )
    if rol not in ROLES:
        f.error("rol", "Elige si eres estudiante o tienda.")
    universidad = f.universidad()
    f.texto("nombre", "tu nombre", 50)
    f.texto("apellido", "tu apellido", 50)
    f.telefono()
    if rol == TIENDA:
        f.texto("nombre_tienda", "el nombre de la tienda", 80)

    if f.valido:
        try:
            usuarios.crear(f["telefono"], f["nombre"], f["apellido"], rol, universidad, f["nombre_tienda"])
            return render(request, "auth/registro_exitoso.html", rol=rol)
        except usuarios.TelefonoRepetido:
            f.error("telefono", "Este teléfono ya está registrado. Inicia sesión.")

    return render(
        request, "auth/registro.html", status_code=400,
        universidades=universidades.listar(), valores=f.valores, errores=f.errores,
    )


# ---------- Inicio de sesión ----------

@router.get("/login")
def mostrar_login(request: Request):
    return render(request, "auth/login.html")


@router.post("/login")
def iniciar_sesion(request: Request, telefono: str = Form("")):
    telefono = telefono.strip()
    if not telefono_valido(telefono):
        return render(request, "auth/login.html", status_code=400, error="El teléfono debe tener 10 dígitos.", telefono=telefono)

    usuario = usuarios.buscar_por_telefono(telefono)
    if usuario is None:
        return render(request, "auth/cuenta_no_encontrada.html", status_code=404)
    if not usuario["activo"]:
        return render(
            request, "auth/login.html", status_code=403,
            error=f"Esta cuenta está suspendida. Escríbenos a {CORREO_SOPORTE}.", telefono=telefono,
        )

    request.session[CLAVE_TELEFONO] = telefono
    return render(request, "auth/verificar.html", telefono=telefono, codigo_prueba=CODIGO_PRUEBA)


@router.post("/verificar-codigo")
def verificar_codigo(request: Request, codigo: str = Form("")):
    telefono = request.session.get(CLAVE_TELEFONO)
    if not telefono:
        return RedirectResponse("/login", 303)

    if codigo.strip() != CODIGO_PRUEBA:
        return render(
            request, "auth/verificar.html", status_code=400, telefono=telefono,
            codigo_prueba=CODIGO_PRUEBA, error="El código no es correcto. Vuelve a intentarlo.",
        )

    usuario = usuarios.buscar_por_telefono(telefono)
    if usuario is None or not usuario["activo"]:
        request.session.pop(CLAVE_TELEFONO, None)
        return RedirectResponse("/login", 303)

    request.session.clear()
    request.session["usuario_id"] = usuario["id"]
    return RedirectResponse(pagina_inicio(usuarios.cargar(usuario["id"])), 303)


@router.get("/logout")
def cerrar_sesion(request: Request):
    request.session.clear()
    return RedirectResponse("/login", 303)


# ---------- Completar perfil (cuentas creadas antes de las universidades) ----------

@router.get("/completar-perfil")
def mostrar_completar_perfil(request: Request, usuario: dict = Depends(usuario_en_sesion)):
    if usuarios.perfil_completo(usuario):
        return RedirectResponse(pagina_inicio(usuario), 303)
    return render(
        request, "auth/completar_perfil.html", universidades=universidades.listar(),
        valores={"universidad_id": str(usuario["universidad_id"] or "")}, errores={},
    )


@router.post("/completar-perfil")
def completar_perfil(
    request: Request,
    universidad_id: str = Form(""),
    nombre_tienda: str = Form(""),
    usuario: dict = Depends(usuario_en_sesion),
):
    f = Formulario(universidad_id=universidad_id, nombre_tienda=nombre_tienda)
    universidad = f.universidad()
    necesita_tienda = usuario["rol"] == TIENDA and usuario["tienda_id"] is None
    if necesita_tienda:
        f.texto("nombre_tienda", "el nombre de la tienda", 80)
    if not f.valido:
        return render(
            request, "auth/completar_perfil.html", status_code=400,
            universidades=universidades.listar(), valores=f.valores, errores=f.errores,
        )
    usuarios.completar_perfil(usuario, universidad, f["nombre_tienda"] if necesita_tienda else None)
    return RedirectResponse(pagina_inicio(usuarios.cargar(usuario["id"])), 303)
