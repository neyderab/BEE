"""Controlador de administración: usuarios, permisos, pedidos y universidades."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.controladores.dependencias import SinPermiso, admin_en_sesion, requiere_permiso
from app.modelos import pedidos, universidades, usuarios
from app.modelos import permisos as P
from app.modelos.usuarios import ADMIN, ESTUDIANTE, TIENDA, TODOS_LOS_ROLES
from app.servicios.validacion import Formulario
from app.vistas.plantillas import mostrar_mensaje, render

router = APIRouter(prefix="/admin")


def ir_a_usuario(usuario_id: int) -> RedirectResponse:
    return RedirectResponse(f"/admin/usuarios/{usuario_id}", 303)


def usuario_no_existe(request: Request):
    return render(request, "errores/error.html", status_code=404, texto="Ese usuario no existe.", volver="/admin/usuarios")


def cargar_objetivo(request: Request, actor: dict, usuario_id: int, accion: str):
    """Carga al usuario sobre el que se va a actuar y aplica las reglas de app/modelos/permisos.py.

    Devuelve (usuario, None) o (None, respuesta de error).
    """
    objetivo = usuarios.cargar(usuario_id)
    if objetivo is None:
        return None, usuario_no_existe(request)
    if objetivo["id"] == actor["id"] and accion != "datos":
        mostrar_mensaje(request, "No puedes cambiar tus propios permisos, suspenderte ni eliminarte.", "error")
        return None, ir_a_usuario(usuario_id)
    if objetivo["rol"] == ADMIN and not P.tiene(actor, P.GESTIONAR_PERMISOS):
        raise SinPermiso()
    return objetivo, None


# ---------- Inicio ----------

@router.get("")
def panel(request: Request, usuario: dict = Depends(admin_en_sesion)):
    return render(
        request, "admin/panel.html", seccion="panel",
        por_rol=usuarios.contar_por_rol(), pedidos=pedidos.resumen_hoy(),
    )


# ---------- Usuarios ----------

@router.get("/usuarios")
def listar_usuarios(
    request: Request, q: str = "", rol: str = "", estado: str = "",
    usuario: dict = Depends(requiere_permiso(P.VER_USUARIOS)),
):
    return render(
        request, "admin/usuarios.html", seccion="usuarios", usuarios=usuarios.listar(q, rol, estado),
        filtros={"q": q, "rol": rol, "estado": estado}, roles=TODOS_LOS_ROLES,
    )


def formulario_nuevo(request: Request, actor: dict, valores: dict, errores: dict, status_code=200):
    roles = TODOS_LOS_ROLES if P.tiene(actor, P.GESTIONAR_PERMISOS) else (ESTUDIANTE, TIENDA)
    return render(
        request, "admin/usuario_nuevo.html", status_code=status_code, seccion="usuarios",
        universidades=universidades.listar(), roles=roles, valores=valores, errores=errores, permisos=P.PERMISOS,
    )


@router.get("/usuarios/nuevo")
def nuevo_usuario(request: Request, usuario: dict = Depends(requiere_permiso(P.CREAR_USUARIOS))):
    return formulario_nuevo(request, usuario, {"rol": ESTUDIANTE, "permisos": []}, {})


@router.post("/usuarios")
def crear_usuario(
    request: Request,
    rol: str = Form(""),
    telefono: str = Form(""),
    nombre: str = Form(""),
    apellido: str = Form(""),
    universidad_id: str = Form(""),
    nombre_tienda: str = Form(""),
    permisos: list[str] = Form([]),
    usuario: dict = Depends(requiere_permiso(P.CREAR_USUARIOS)),
):
    f = Formulario(
        rol=rol, telefono=telefono, nombre=nombre, apellido=apellido,
        universidad_id=universidad_id, nombre_tienda=nombre_tienda, permisos=permisos,
    )
    if rol not in TODOS_LOS_ROLES:
        f.error("rol", "Elige el tipo de usuario.")
    elif rol == ADMIN and not P.tiene(usuario, P.GESTIONAR_PERMISOS):
        raise SinPermiso()
    f.telefono()
    f.texto("nombre", "el nombre", 50)
    f.texto("apellido", "el apellido", 50)
    universidad = f.universidad() if rol in (ESTUDIANTE, TIENDA) else None
    if rol == TIENDA:
        f.texto("nombre_tienda", "el nombre de la tienda", 80)
    otorgados = P.elegibles(usuario, permisos) if rol == ADMIN else set()
    if rol == ADMIN and not otorgados:
        f.error("permisos", "Elige al menos un permiso para el administrador.")

    if f.valido:
        try:
            nuevo_id = usuarios.crear(
                f["telefono"], f["nombre"], f["apellido"], rol, universidad, f["nombre_tienda"], otorgados
            )
            mostrar_mensaje(request, f"Usuario {f['nombre']} {f['apellido']} creado.")
            return ir_a_usuario(nuevo_id)
        except usuarios.TelefonoRepetido:
            f.error("telefono", "Ya existe un usuario con este teléfono.")

    return formulario_nuevo(request, usuario, f.valores, f.errores, status_code=400)


@router.get("/usuarios/{usuario_id}")
def ver_usuario(request: Request, usuario_id: int, usuario: dict = Depends(requiere_permiso(P.VER_USUARIOS))):
    objetivo = usuarios.cargar(usuario_id)
    if objetivo is None:
        return usuario_no_existe(request)
    return render(
        request, "admin/usuario.html", seccion="usuarios", objetivo=objetivo,
        resumen=usuarios.resumen_pedidos(objetivo), universidades=universidades.listar(),
        permisos=P.PERMISOS, errores={},
    )


@router.post("/usuarios/{usuario_id}/datos")
def editar_datos(
    request: Request,
    usuario_id: int,
    nombre: str = Form(""),
    apellido: str = Form(""),
    universidad_id: str = Form(""),
    nombre_tienda: str = Form(""),
    usuario: dict = Depends(requiere_permiso(P.EDITAR_USUARIOS)),
):
    objetivo, error = cargar_objetivo(request, usuario, usuario_id, "datos")
    if error:
        return error

    f = Formulario(nombre=nombre, apellido=apellido, universidad_id=universidad_id, nombre_tienda=nombre_tienda)
    f.texto("nombre", "el nombre", 50)
    f.texto("apellido", "el apellido", 50)
    universidad = f.universidad() if objetivo["rol"] != ADMIN else None  # None: no se cambia.
    if objetivo["tienda_id"]:
        f.texto("nombre_tienda", "el nombre de la tienda", 80)
    if not f.valido:
        mostrar_mensaje(request, " ".join(f.errores.values()), "error")
        return ir_a_usuario(usuario_id)

    usuarios.actualizar_datos(
        objetivo, f["nombre"], f["apellido"], universidad,
        f["nombre_tienda"] if objetivo["tienda_id"] else None,
    )
    mostrar_mensaje(request, "Datos actualizados.")
    return ir_a_usuario(usuario_id)


@router.post("/usuarios/{usuario_id}/permisos")
def editar_permisos(
    request: Request,
    usuario_id: int,
    permisos: list[str] = Form([]),
    usuario: dict = Depends(requiere_permiso(P.GESTIONAR_PERMISOS)),
):
    objetivo, error = cargar_objetivo(request, usuario, usuario_id, "permisos")
    if error:
        return error
    if objetivo["rol"] != ADMIN:
        mostrar_mensaje(request, "Solo los administradores tienen permisos.", "error")
        return ir_a_usuario(usuario_id)

    nuevos = P.combinar(usuario, objetivo["permisos"], permisos)
    if not nuevos:
        mostrar_mensaje(request, "Un administrador necesita al menos un permiso. Si no debe tener acceso, suspéndelo.", "error")
        return ir_a_usuario(usuario_id)

    usuarios.guardar_permisos(usuario_id, nuevos)
    mostrar_mensaje(request, "Permisos actualizados.")
    return ir_a_usuario(usuario_id)


@router.post("/usuarios/{usuario_id}/estado")
def cambiar_estado_cuenta(
    request: Request, usuario_id: int, activo: str = Form(""),
    usuario: dict = Depends(requiere_permiso(P.EDITAR_USUARIOS)),
):
    objetivo, error = cargar_objetivo(request, usuario, usuario_id, "estado")
    if error:
        return error
    activar = activo == "1"
    usuarios.cambiar_activo(usuario_id, activar)
    mostrar_mensaje(request, "Cuenta reactivada." if activar else "Cuenta suspendida: ya no puede iniciar sesión.")
    return ir_a_usuario(usuario_id)


@router.post("/usuarios/{usuario_id}/eliminar")
def eliminar_usuario(request: Request, usuario_id: int, usuario: dict = Depends(requiere_permiso(P.ELIMINAR_USUARIOS))):
    objetivo, error = cargar_objetivo(request, usuario, usuario_id, "eliminar")
    if error:
        return error
    en_curso = usuarios.pedidos_en_curso(objetivo)
    if en_curso:
        mostrar_mensaje(
            request,
            f"Tiene {en_curso} pedido(s) en curso. Espera a que se entreguen o se cancelen, o suspende la cuenta mientras tanto.",
            "error",
        )
        return ir_a_usuario(usuario_id)
    usuarios.eliminar(usuario_id)
    mostrar_mensaje(request, f"Se eliminó la cuenta de {objetivo['nombre']} {objetivo['apellido']}.")
    return RedirectResponse("/admin/usuarios", 303)


# ---------- Pedidos ----------

@router.get("/pedidos")
def ver_pedidos(
    request: Request, universidad_id: str = "", estado: str = "",
    usuario: dict = Depends(requiere_permiso(P.VER_PEDIDOS)),
):
    return render(
        request, "admin/pedidos.html", seccion="pedidos",
        pedidos=pedidos.listar_todos(int(universidad_id) if universidad_id.isdigit() else None, estado),
        universidades=universidades.listar(), filtros={"universidad_id": universidad_id, "estado": estado},
    )


# ---------- Universidades ----------

def pagina_universidades(request: Request, valores: dict, errores: dict, status_code=200):
    return render(
        request, "admin/universidades.html", status_code=status_code, seccion="universidades",
        universidades=universidades.listar_con_conteos(), valores=valores, errores=errores,
    )


@router.get("/universidades")
def ver_universidades(request: Request, usuario: dict = Depends(requiere_permiso(P.GESTIONAR_UNIVERSIDADES))):
    return pagina_universidades(request, {}, {})


@router.post("/universidades")
def crear_universidad(
    request: Request, nombre: str = Form(""), ciudad: str = Form(""),
    usuario: dict = Depends(requiere_permiso(P.GESTIONAR_UNIVERSIDADES)),
):
    f = Formulario(nombre=nombre, ciudad=ciudad)
    f.texto("nombre", "el nombre de la universidad", 120)
    f.texto("ciudad", "la ciudad", 60)
    if f.valido:
        if universidades.crear(f["nombre"], f["ciudad"]):
            mostrar_mensaje(request, f"Universidad «{f['nombre']}» agregada.")
            return RedirectResponse("/admin/universidades", 303)
        f.error("nombre", "Esa universidad ya existe.")
    return pagina_universidades(request, f.valores, f.errores, status_code=400)
