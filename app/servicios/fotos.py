"""Fotos subidas por los usuarios (perfil y productos)."""

import io

from fastapi import UploadFile
from fastapi.responses import Response
from PIL import Image, ImageOps, UnidentifiedImageError

FOTO_MAXIMA_BYTES = 5 * 1024 * 1024


async def leer_foto(archivo: UploadFile, lado: int) -> tuple[bytes | None, str | None]:
    """Valida la imagen y la convierte en un JPEG cuadrado de `lado`×`lado`.

    Devuelve (jpeg, None) o (None, mensaje de error).
    """
    contenido = await archivo.read(FOTO_MAXIMA_BYTES + 1)
    if len(contenido) > FOTO_MAXIMA_BYTES:
        return None, "La foto pesa más de 5 MB. Elige una más liviana."
    try:
        imagen = ImageOps.exif_transpose(Image.open(io.BytesIO(contenido))).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return None, "El archivo no es una imagen válida (usa JPG, PNG o WebP)."
    salida = io.BytesIO()
    ImageOps.fit(imagen, (lado, lado), Image.LANCZOS).save(salida, "JPEG", quality=85, optimize=True)
    return salida.getvalue(), None


def respuesta_foto(fila: dict | None) -> Response:
    """La URL lleva ?v=<versión>, así que el navegador puede guardarla en caché."""
    if fila is None:
        return Response(status_code=404)
    return Response(bytes(fila["foto"]), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})
