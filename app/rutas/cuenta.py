"""Notificaciones, configuración del perfil, foto y cierre de cuenta."""

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.db import conectar, ejecutar, uno
from app.fotos import leer_foto, respuesta_foto
from app.pedidos import ACTIVOS, contar_sin_leer, notificaciones_recientes
from app.plantillas import mostrar_mensaje, render
from app.sesion import ADMIN, ESTUDIANTE, TIENDA, usuario_en_sesion
from app.validacion import Formulario

router = APIRouter()

CONFIRMACION_CIERRE = "ELIMINAR"


def volver_a_configuracion() -> RedirectResponse:
    return RedirectResponse("/configuracion", 303)


# ---------- Notificaciones ----------

@router.get("/notificaciones")
def ver_notificaciones(request: Request, usuario: dict = Depends(usuario_en_sesion)):
    notificaciones = notificaciones_recientes(usuario["id"], limite=50)
    marcar_leidas(usuario["id"])
    return render(request, "notificaciones.html", notificaciones=notificaciones)


@router.get("/notificaciones/resumen")
def resumen_notificaciones(usuario: dict = Depends(usuario_en_sesion)):
    """Lo consulta la página cada pocos segundos para avisar de novedades."""
    recientes = notificaciones_recientes(usuario["id"], limite=1)
    ultima = recientes[0] if recientes else {"id": 0, "texto": ""}
    return JSONResponse(
        {"sin_leer": contar_sin_leer(usuario["id"]), "ultima_id": ultima["id"], "ultima_texto": ultima["texto"]}
    )


@router.post("/notificaciones/leidas")
def marcar_todas_leidas(request: Request, usuario: dict = Depends(usuario_en_sesion)):
    marcar_leidas(usuario["id"])
    if request.headers.get("x-requested-with") == "fetch":
        return Response(status_code=204)
    return RedirectResponse(request.headers.get("referer") or "/", 303)


def marcar_leidas(usuario_id: int) -> None:
    ejecutar("UPDATE notificaciones SET leida = TRUE WHERE usuario_id = %s AND NOT leida", (usuario_id,))


# ---------- Configuración ----------

@router.get("/configuracion")
def ver_configuracion(request: Request, usuario: dict = Depends(usuario_en_sesion)):
    return render(request, "configuracion.html", errores={}, valores=usuario)


@router.post("/configuracion/perfil")
def guardar_perfil(
    request: Request,
    nombre: str = Form(""),
    apellido: str = Form(""),
    nombre_tienda: str = Form(""),
    usuario: dict = Depends(usuario_en_sesion),
):
    f = Formulario(**{**usuario, "nombre": nombre, "apellido": apellido, "tienda": nombre_tienda})
    f.texto("nombre", "tu nombre", 50)
    f.texto("apellido", "tu apellido", 50)
    es_tienda = usuario["rol"] == TIENDA and usuario["tienda_id"]
    if es_tienda:
        f.texto("tienda", "el nombre de la tienda", 80)
    if not f.valido:
        return render(request, "configuracion.html", status_code=400, errores=f.errores, valores=f.valores)

    with conectar() as conexion:
        conexion.execute(
            "UPDATE usuarios SET nombre = %s, apellido = %s WHERE id = %s",
            (f["nombre"], f["apellido"], usuario["id"]),
        )
        if es_tienda:
            conexion.execute("UPDATE tiendas SET nombre = %s WHERE id = %s", (f["tienda"], usuario["tienda_id"]))
    mostrar_mensaje(request, "Tus datos se guardaron.")
    return volver_a_configuracion()


# ---------- Foto de perfil ----------

@router.post("/configuracion/foto")
async def subir_foto(request: Request, foto: UploadFile = File(...), usuario: dict = Depends(usuario_en_sesion)):
    jpeg, error = await leer_foto(foto, 256)
    if error:
        mostrar_mensaje(request, error, "error")
    else:
        ejecutar("UPDATE usuarios SET foto = %s, foto_actualizada = now() WHERE id = %s", (jpeg, usuario["id"]))
        mostrar_mensaje(request, "Tu foto de perfil se actualizó.")
    return volver_a_configuracion()


@router.post("/configuracion/foto/eliminar")
def eliminar_foto(request: Request, usuario: dict = Depends(usuario_en_sesion)):
    ejecutar("UPDATE usuarios SET foto = NULL, foto_actualizada = NULL WHERE id = %s", (usuario["id"],))
    mostrar_mensaje(request, "Quitaste tu foto de perfil.")
    return volver_a_configuracion()


@router.get("/fotos/{usuario_id}")
def ver_foto(usuario_id: int, usuario: dict = Depends(usuario_en_sesion)):
    return respuesta_foto(uno("SELECT foto FROM usuarios WHERE id = %s AND foto IS NOT NULL", (usuario_id,)))


@router.get("/productos/{producto_id}/foto")
def ver_foto_producto(producto_id: int, usuario: dict = Depends(usuario_en_sesion)):
    return respuesta_foto(uno("SELECT foto FROM productos WHERE id = %s AND foto IS NOT NULL", (producto_id,)))


# ---------- Cerrar la cuenta ----------

@router.post("/configuracion/cerrar-cuenta")
def cerrar_cuenta(
    request: Request,
    confirmacion: str = Form(""),
    usuario: dict = Depends(usuario_en_sesion),
):
    if usuario["rol"] == ADMIN:
        mostrar_mensaje(request, "Pide a otro administrador que elimine tu cuenta.", "error")
        return volver_a_configuracion()
    if usuario["rol"] != ESTUDIANTE:
        # Las tiendas cierran su cuenta escribiendo al correo de soporte.
        mostrar_mensaje(request, "Para cerrar la cuenta de una tienda escríbenos por correo.", "error")
        return volver_a_configuracion()

    if confirmacion.strip().upper() != CONFIRMACION_CIERRE:
        mostrar_mensaje(
            request, f"Escribe {CONFIRMACION_CIERRE} para confirmar el cierre de tu cuenta.", "error"
        )
        return volver_a_configuracion()

    with conectar() as conexion:
        en_curso = conexion.execute(
            "SELECT COUNT(*) AS n FROM pedidos WHERE estudiante_id = %s AND estado = ANY(%s)",
            (usuario["id"], list(ACTIVOS)),
        ).fetchone()["n"]
        if en_curso:
            mostrar_mensaje(
                request,
                "Tienes pedidos en curso. Podrás cerrar tu cuenta cuando se entreguen o se cancelen.",
                "error",
            )
            return volver_a_configuracion()
        # Sus pedidos pasados quedan en el historial de la tienda sin sus datos.
        conexion.execute("DELETE FROM usuarios WHERE id = %s", (usuario["id"],))

    request.session.clear()
    return render(request, "cuenta_cerrada.html", usuario=None)
