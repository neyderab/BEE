"""Notificaciones, configuración del perfil, foto y cierre de cuenta."""

import io

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response
from PIL import Image, ImageOps, UnidentifiedImageError

from app.db import conectar
from app.pedidos import ACTIVOS, contar_sin_leer, notificaciones_recientes
from app.plantillas import mostrar_mensaje, render
from app.sesion import ADMIN, ESTUDIANTE, TIENDA, usuario_en_sesion

router = APIRouter()

FOTO_MAXIMA_BYTES = 5 * 1024 * 1024
FOTO_LADO = 256
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
    return JSONResponse(
        {
            "sin_leer": contar_sin_leer(usuario["id"]),
            "ultima_id": recientes[0]["id"] if recientes else 0,
            "ultima_texto": recientes[0]["texto"] if recientes else "",
        }
    )


@router.post("/notificaciones/leidas")
def marcar_todas_leidas(request: Request, usuario: dict = Depends(usuario_en_sesion)):
    marcar_leidas(usuario["id"])
    if request.headers.get("x-requested-with") == "fetch":
        return Response(status_code=204)
    return RedirectResponse(request.headers.get("referer") or "/", 303)


def marcar_leidas(usuario_id: int) -> None:
    with conectar() as conexion:
        conexion.execute(
            "UPDATE notificaciones SET leida = TRUE WHERE usuario_id = %s AND NOT leida",
            (usuario_id,),
        )


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
    valores = {
        **usuario,
        "nombre": nombre.strip(),
        "apellido": apellido.strip(),
        "tienda": nombre_tienda.strip(),
    }
    errores = {}
    for campo, etiqueta in (("nombre", "tu nombre"), ("apellido", "tu apellido")):
        if not valores[campo]:
            errores[campo] = f"Escribe {etiqueta}."
        elif len(valores[campo]) > 50:
            errores[campo] = "Máximo 50 caracteres."
    es_tienda = usuario["rol"] == TIENDA and usuario["tienda_id"]
    if es_tienda and not 0 < len(valores["tienda"]) <= 80:
        errores["tienda"] = "Escribe el nombre de la tienda (máximo 80 caracteres)."

    if errores:
        return render(
            request, "configuracion.html", status_code=400, errores=errores, valores=valores
        )

    with conectar() as conexion:
        conexion.execute(
            "UPDATE usuarios SET nombre = %s, apellido = %s WHERE id = %s",
            (valores["nombre"], valores["apellido"], usuario["id"]),
        )
        if es_tienda:
            conexion.execute(
                "UPDATE tiendas SET nombre = %s WHERE id = %s",
                (valores["tienda"], usuario["tienda_id"]),
            )
    mostrar_mensaje(request, "Tus datos se guardaron.")
    return volver_a_configuracion()


# ---------- Foto de perfil ----------

def preparar_foto(contenido: bytes) -> bytes | None:
    """Valida la imagen y la convierte en un JPEG cuadrado de 256×256."""
    try:
        imagen = Image.open(io.BytesIO(contenido))
        imagen = ImageOps.exif_transpose(imagen).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return None
    imagen = ImageOps.fit(imagen, (FOTO_LADO, FOTO_LADO), Image.LANCZOS)
    salida = io.BytesIO()
    imagen.save(salida, "JPEG", quality=85, optimize=True)
    return salida.getvalue()


@router.post("/configuracion/foto")
async def subir_foto(
    request: Request,
    foto: UploadFile = File(...),
    usuario: dict = Depends(usuario_en_sesion),
):
    contenido = await foto.read(FOTO_MAXIMA_BYTES + 1)
    if len(contenido) > FOTO_MAXIMA_BYTES:
        mostrar_mensaje(request, "La foto pesa más de 5 MB. Elige una más liviana.", "error")
        return volver_a_configuracion()
    jpeg = preparar_foto(contenido)
    if jpeg is None:
        mostrar_mensaje(request, "El archivo no es una imagen válida (usa JPG, PNG o WebP).", "error")
        return volver_a_configuracion()
    with conectar() as conexion:
        conexion.execute(
            "UPDATE usuarios SET foto = %s, foto_actualizada = now() WHERE id = %s",
            (jpeg, usuario["id"]),
        )
    mostrar_mensaje(request, "Tu foto de perfil se actualizó.")
    return volver_a_configuracion()


@router.post("/configuracion/foto/eliminar")
def eliminar_foto(request: Request, usuario: dict = Depends(usuario_en_sesion)):
    with conectar() as conexion:
        conexion.execute(
            "UPDATE usuarios SET foto = NULL, foto_actualizada = NULL WHERE id = %s",
            (usuario["id"],),
        )
    mostrar_mensaje(request, "Quitaste tu foto de perfil.")
    return volver_a_configuracion()


@router.get("/fotos/{usuario_id}")
def ver_foto(usuario_id: int, usuario: dict = Depends(usuario_en_sesion)):
    with conectar() as conexion:
        fila = conexion.execute(
            "SELECT foto FROM usuarios WHERE id = %s AND foto IS NOT NULL", (usuario_id,)
        ).fetchone()
    if fila is None:
        return Response(status_code=404)
    # La URL lleva ?v=<versión>, así que el navegador puede guardarla en caché.
    return Response(
        bytes(fila["foto"]),
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=86400"},
    )


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
