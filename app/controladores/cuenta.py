"""Controlador de la cuenta: avisos, configuración del perfil, fotos y eliminar la cuenta."""

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.controladores.dependencias import usuario_en_sesion
from app.modelos import menus, notificaciones, usuarios
from app.modelos.usuarios import ADMIN, ESTUDIANTE, TIENDA
from app.servicios.fotos import leer_foto, respuesta_foto
from app.servicios.validacion import Formulario
from app.vistas.plantillas import mostrar_mensaje, render

router = APIRouter()

CONFIRMACION_CIERRE = "ELIMINAR"


def volver_a_configuracion() -> RedirectResponse:
    return RedirectResponse("/configuracion", 303)


# ---------- Avisos (campana) ----------

@router.get("/notificaciones")
def ver_notificaciones(request: Request, usuario: dict = Depends(usuario_en_sesion)):
    lista = notificaciones.recientes(usuario["id"], limite=50)
    notificaciones.marcar_leidas(usuario["id"])
    return render(request, "cuenta/notificaciones.html", notificaciones=lista)


@router.get("/notificaciones/resumen")
def resumen_notificaciones(usuario: dict = Depends(usuario_en_sesion)):
    """Lo consulta la página cada pocos segundos para avisar de novedades."""
    recientes = notificaciones.recientes(usuario["id"], limite=1)
    ultima = recientes[0] if recientes else {"id": 0, "texto": ""}
    return JSONResponse(
        {"sin_leer": notificaciones.contar_sin_leer(usuario["id"]), "ultima_id": ultima["id"], "ultima_texto": ultima["texto"]}
    )


@router.post("/notificaciones/leidas")
def marcar_todas_leidas(request: Request, usuario: dict = Depends(usuario_en_sesion)):
    notificaciones.marcar_leidas(usuario["id"])
    if request.headers.get("x-requested-with") == "fetch":
        return Response(status_code=204)
    return RedirectResponse(request.headers.get("referer") or "/", 303)


# ---------- Configuración ----------

@router.get("/configuracion")
def ver_configuracion(request: Request, usuario: dict = Depends(usuario_en_sesion)):
    return render(request, "cuenta/configuracion.html", errores={}, valores=usuario)


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
        return render(request, "cuenta/configuracion.html", status_code=400, errores=f.errores, valores=f.valores)

    usuarios.actualizar_datos(usuario, f["nombre"], f["apellido"], nombre_tienda=f["tienda"] if es_tienda else None)
    mostrar_mensaje(request, "Tus datos se guardaron.")
    return volver_a_configuracion()


# ---------- Fotos ----------

@router.post("/configuracion/foto")
async def subir_foto(request: Request, foto: UploadFile = File(...), usuario: dict = Depends(usuario_en_sesion)):
    jpeg, error = await leer_foto(foto, 256)
    if error:
        mostrar_mensaje(request, error, "error")
    else:
        usuarios.guardar_foto(usuario["id"], jpeg)
        mostrar_mensaje(request, "Tu foto de perfil se actualizó.")
    return volver_a_configuracion()


@router.post("/configuracion/foto/eliminar")
def eliminar_foto(request: Request, usuario: dict = Depends(usuario_en_sesion)):
    usuarios.guardar_foto(usuario["id"], None)
    mostrar_mensaje(request, "Quitaste tu foto de perfil.")
    return volver_a_configuracion()


@router.get("/fotos/{usuario_id}")
def ver_foto(usuario_id: int, usuario: dict = Depends(usuario_en_sesion)):
    return respuesta_foto(usuarios.foto(usuario_id))


@router.get("/productos/{producto_id}/foto")
def ver_foto_producto(producto_id: int, usuario: dict = Depends(usuario_en_sesion)):
    return respuesta_foto(menus.foto_producto(producto_id))


# ---------- Eliminar la cuenta ----------

@router.post("/configuracion/cerrar-cuenta")
def cerrar_cuenta(request: Request, confirmacion: str = Form(""), usuario: dict = Depends(usuario_en_sesion)):
    if usuario["rol"] == ADMIN:
        mostrar_mensaje(request, "Pide a otro administrador que elimine tu cuenta.", "error")
        return volver_a_configuracion()
    if usuario["rol"] != ESTUDIANTE:
        # Las tiendas cierran su cuenta escribiendo al correo de soporte.
        mostrar_mensaje(request, "Para cerrar la cuenta de una tienda escríbenos por correo.", "error")
        return volver_a_configuracion()
    if confirmacion.strip().upper() != CONFIRMACION_CIERRE:
        mostrar_mensaje(request, f"Escribe {CONFIRMACION_CIERRE} para confirmar el cierre de tu cuenta.", "error")
        return volver_a_configuracion()
    if usuarios.pedidos_en_curso(usuario):
        mostrar_mensaje(request, "Tienes pedidos en curso. Podrás cerrar tu cuenta cuando se entreguen o se cancelen.", "error")
        return volver_a_configuracion()

    usuarios.eliminar(usuario["id"])  # Sus pedidos pasados quedan en el historial de la tienda sin sus datos.
    request.session.clear()
    return render(request, "cuenta/cuenta_cerrada.html", usuario=None)
