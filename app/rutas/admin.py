"""Panel de administración: usuarios, permisos, pedidos y universidades."""

import psycopg
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app import permisos as P
from app.db import campos_foto, conectar, ejecutar, listar_universidades, todos, uno
from app.pedidos import ACTIVOS, ESTADOS
from app.plantillas import mostrar_mensaje, render
from app.sesion import (
    ADMIN,
    ESTUDIANTE,
    TIENDA,
    TODOS_LOS_ROLES,
    SinPermiso,
    admin_en_sesion,
    cargar_usuario,
    requiere_permiso,
)
from app.usuarios import guardar_permisos, insertar_usuario
from app.validacion import Formulario

router = APIRouter(prefix="/admin")


def ir_a_usuario(usuario_id: int) -> RedirectResponse:
    return RedirectResponse(f"/admin/usuarios/{usuario_id}", 303)


def usuario_no_existe(request: Request):
    return render(
        request, "error.html", status_code=404, texto="Ese usuario no existe.", volver="/admin/usuarios"
    )


def cargar_objetivo(request: Request, actor: dict, usuario_id: int, accion: str):
    """Carga al usuario sobre el que se va a actuar y aplica las reglas de app/permisos.py.

    Devuelve (usuario, None) o (None, respuesta de error).
    """
    objetivo = cargar_usuario(usuario_id)
    if objetivo is None:
        return None, usuario_no_existe(request)
    if objetivo["id"] == actor["id"] and accion != "datos":
        mostrar_mensaje(request, "No puedes cambiar tus propios permisos, suspenderte ni eliminarte.", "error")
        return None, ir_a_usuario(usuario_id)
    if objetivo["rol"] == ADMIN and not P.tiene(actor, P.GESTIONAR_PERMISOS):
        raise SinPermiso()
    return objetivo, None


def permisos_elegidos(actor: dict, elegidos: list[str]) -> set[str]:
    """Solo se pueden dar permisos que existen y que quien los da también tiene."""
    return set(elegidos) & set(P.TODOS) & set(actor["permisos"])


def filtro_sql(condiciones: list[tuple[str, list]]) -> tuple[str, list]:
    """[("u.rol = %s", ["Tienda"]), ...] -> ("WHERE u.rol = %s AND ...", ["Tienda", ...])."""
    if not condiciones:
        return "", []
    return "WHERE " + " AND ".join(c for c, _ in condiciones), [p for _, ps in condiciones for p in ps]


# ---------- Inicio ----------

@router.get("")
def panel(request: Request, usuario: dict = Depends(admin_en_sesion)):
    por_rol = {f["rol"]: f["n"] for f in todos("SELECT rol, COUNT(*) AS n FROM usuarios GROUP BY rol")}
    pedidos = uno(
        """
        SELECT COUNT(*) FILTER (WHERE creado_en >= date_trunc('day', now())) AS hoy,
               COUNT(*) FILTER (WHERE estado = ANY(%s)) AS en_curso
        FROM pedidos
        """,
        (list(ACTIVOS),),
    )
    return render(request, "admin/panel.html", seccion="panel", por_rol=por_rol, pedidos=pedidos)


# ---------- Usuarios ----------

@router.get("/usuarios")
def listar_usuarios(
    request: Request,
    q: str = "",
    rol: str = "",
    estado: str = "",
    usuario: dict = Depends(requiere_permiso(P.VER_USUARIOS)),
):
    condiciones = []
    if q.strip():
        patron = f"%{q.strip()}%"
        condiciones.append((
            "(u.nombre || ' ' || u.apellido ILIKE %s OR u.telefono LIKE %s OR t.nombre ILIKE %s)",
            [patron, patron, patron],
        ))
    if rol in TODOS_LOS_ROLES:
        condiciones.append(("u.rol = %s", [rol]))
    if estado in ("activo", "suspendido"):
        condiciones.append(("u.activo" if estado == "activo" else "NOT u.activo", []))
    donde, parametros = filtro_sql(condiciones)

    usuarios = todos(
        f"""
        SELECT u.id, u.nombre, u.apellido, u.telefono, u.rol, u.activo, u.creado_en,
               un.nombre AS universidad, t.nombre AS tienda, {campos_foto("u")}
        FROM usuarios u
        LEFT JOIN universidades un ON un.id = u.universidad_id
        LEFT JOIN tiendas t ON t.usuario_id = u.id
        {donde}
        ORDER BY u.creado_en DESC, u.id DESC
        LIMIT 200
        """,
        parametros,
    )
    return render(
        request, "admin/usuarios.html", seccion="usuarios", usuarios=usuarios,
        filtros={"q": q, "rol": rol, "estado": estado}, roles=TODOS_LOS_ROLES,
    )


def formulario_nuevo(request: Request, actor: dict, valores: dict, errores: dict, status_code=200):
    roles = TODOS_LOS_ROLES if P.tiene(actor, P.GESTIONAR_PERMISOS) else (ESTUDIANTE, TIENDA)
    return render(
        request, "admin/usuario_nuevo.html", status_code=status_code, seccion="usuarios",
        universidades=listar_universidades(), roles=roles, valores=valores, errores=errores,
        permisos=P.PERMISOS,
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
    otorgados = permisos_elegidos(usuario, permisos) if rol == ADMIN else set()
    if rol == ADMIN and not otorgados:
        f.error("permisos", "Elige al menos un permiso para el administrador.")

    if f.valido:
        try:
            with conectar() as conexion:
                nuevo_id = insertar_usuario(
                    conexion, f["telefono"], f["nombre"], f["apellido"],
                    rol, universidad, f["nombre_tienda"], otorgados,
                )
            mostrar_mensaje(request, f"Usuario {f['nombre']} {f['apellido']} creado.")
            return ir_a_usuario(nuevo_id)
        except psycopg.errors.UniqueViolation:
            f.error("telefono", "Ya existe un usuario con este teléfono.")

    return formulario_nuevo(request, usuario, f.valores, f.errores, status_code=400)


@router.get("/usuarios/{usuario_id}")
def ver_usuario(request: Request, usuario_id: int, usuario: dict = Depends(requiere_permiso(P.VER_USUARIOS))):
    objetivo = cargar_usuario(usuario_id)
    if objetivo is None:
        return usuario_no_existe(request)
    resumen = uno(
        """
        SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE estado = ANY(%s)) AS en_curso
        FROM pedidos WHERE estudiante_id = %s OR tienda_id = %s
        """,
        (list(ACTIVOS), usuario_id, objetivo["tienda_id"]),
    )
    return render(
        request, "admin/usuario.html", seccion="usuarios", objetivo=objetivo, resumen=resumen,
        universidades=listar_universidades(), permisos=P.PERMISOS, errores={},
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
    universidad = f.universidad() if objetivo["rol"] != ADMIN else objetivo["universidad_id"]
    if objetivo["tienda_id"]:
        f.texto("nombre_tienda", "el nombre de la tienda", 80)
    if not f.valido:
        mostrar_mensaje(request, " ".join(f.errores.values()), "error")
        return ir_a_usuario(usuario_id)

    with conectar() as conexion:
        conexion.execute(
            "UPDATE usuarios SET nombre = %s, apellido = %s, universidad_id = %s WHERE id = %s",
            (f["nombre"], f["apellido"], universidad, usuario_id),
        )
        if objetivo["tienda_id"]:
            conexion.execute(
                "UPDATE tiendas SET nombre = %s WHERE id = %s", (f["nombre_tienda"], objetivo["tienda_id"])
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

    # Los permisos que quien edita no tiene se conservan tal como estaban.
    ajenos = set(objetivo["permisos"]) - set(usuario["permisos"])
    nuevos = ajenos | permisos_elegidos(usuario, permisos)
    if not nuevos:
        mostrar_mensaje(
            request, "Un administrador necesita al menos un permiso. Si no debe tener acceso, suspéndelo.", "error"
        )
        return ir_a_usuario(usuario_id)

    with conectar() as conexion:
        guardar_permisos(conexion, usuario_id, nuevos)
    mostrar_mensaje(request, "Permisos actualizados.")
    return ir_a_usuario(usuario_id)


@router.post("/usuarios/{usuario_id}/estado")
def cambiar_estado_cuenta(
    request: Request,
    usuario_id: int,
    activo: str = Form(""),
    usuario: dict = Depends(requiere_permiso(P.EDITAR_USUARIOS)),
):
    objetivo, error = cargar_objetivo(request, usuario, usuario_id, "estado")
    if error:
        return error
    activar = activo == "1"
    ejecutar("UPDATE usuarios SET activo = %s WHERE id = %s", (activar, usuario_id))
    mostrar_mensaje(request, "Cuenta reactivada." if activar else "Cuenta suspendida: ya no puede iniciar sesión.")
    return ir_a_usuario(usuario_id)


@router.post("/usuarios/{usuario_id}/eliminar")
def eliminar_usuario(request: Request, usuario_id: int, usuario: dict = Depends(requiere_permiso(P.ELIMINAR_USUARIOS))):
    objetivo, error = cargar_objetivo(request, usuario, usuario_id, "eliminar")
    if error:
        return error
    with conectar() as conexion:
        en_curso = conexion.execute(
            "SELECT COUNT(*) AS n FROM pedidos WHERE (estudiante_id = %s OR tienda_id = %s) AND estado = ANY(%s)",
            (usuario_id, objetivo["tienda_id"], list(ACTIVOS)),
        ).fetchone()["n"]
        if en_curso:
            mostrar_mensaje(
                request,
                f"Tiene {en_curso} pedido(s) en curso. Espera a que se entreguen o se cancelen, "
                "o suspende la cuenta mientras tanto.",
                "error",
            )
            return ir_a_usuario(usuario_id)
        conexion.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))

    mostrar_mensaje(request, f"Se eliminó la cuenta de {objetivo['nombre']} {objetivo['apellido']}.")
    return RedirectResponse("/admin/usuarios", 303)


# ---------- Pedidos ----------

@router.get("/pedidos")
def ver_pedidos(
    request: Request,
    universidad_id: str = "",
    estado: str = "",
    usuario: dict = Depends(requiere_permiso(P.VER_PEDIDOS)),
):
    condiciones = []
    if universidad_id.isdigit():
        condiciones.append(("dueno.universidad_id = %s", [int(universidad_id)]))
    if estado in ESTADOS:
        condiciones.append(("p.estado = %s", [estado]))
    donde, parametros = filtro_sql(condiciones)
    pedidos = todos(
        f"""
        SELECT p.id, p.estado, p.total, p.creado_en, p.estudiante_id,
               t.nombre AS tienda, un.nombre AS universidad, e.nombre, e.apellido
        FROM pedidos p
        JOIN tiendas t ON t.id = p.tienda_id
        JOIN usuarios dueno ON dueno.id = t.usuario_id
        LEFT JOIN universidades un ON un.id = dueno.universidad_id
        LEFT JOIN usuarios e ON e.id = p.estudiante_id
        {donde}
        ORDER BY p.creado_en DESC
        LIMIT 100
        """,
        parametros,
    )
    return render(
        request, "admin/pedidos.html", seccion="pedidos", pedidos=pedidos,
        universidades=listar_universidades(), filtros={"universidad_id": universidad_id, "estado": estado},
    )


# ---------- Universidades ----------

def pagina_universidades(request: Request, valores: dict, errores: dict, status_code=200):
    universidades = todos(
        """
        SELECT un.id, un.nombre, un.ciudad,
               COUNT(u.id) FILTER (WHERE u.rol = 'Estudiante') AS estudiantes,
               COUNT(u.id) FILTER (WHERE u.rol = 'Tienda') AS tiendas
        FROM universidades un
        LEFT JOIN usuarios u ON u.universidad_id = un.id
        GROUP BY un.id
        ORDER BY un.nombre
        """
    )
    return render(
        request, "admin/universidades.html", status_code=status_code, seccion="universidades",
        universidades=universidades, valores=valores, errores=errores,
    )


@router.get("/universidades")
def ver_universidades(request: Request, usuario: dict = Depends(requiere_permiso(P.GESTIONAR_UNIVERSIDADES))):
    return pagina_universidades(request, {}, {})


@router.post("/universidades")
def crear_universidad(
    request: Request,
    nombre: str = Form(""),
    ciudad: str = Form(""),
    usuario: dict = Depends(requiere_permiso(P.GESTIONAR_UNIVERSIDADES)),
):
    f = Formulario(nombre=nombre, ciudad=ciudad)
    f.texto("nombre", "el nombre de la universidad", 120)
    f.texto("ciudad", "la ciudad", 60)
    if f.valido:
        try:
            ejecutar("INSERT INTO universidades (nombre, ciudad) VALUES (%s, %s)", (f["nombre"], f["ciudad"]))
            mostrar_mensaje(request, f"Universidad «{f['nombre']}» agregada.")
            return RedirectResponse("/admin/universidades", 303)
        except psycopg.errors.UniqueViolation:
            f.error("nombre", "Esa universidad ya existe.")
    return pagina_universidades(request, f.valores, f.errores, status_code=400)
