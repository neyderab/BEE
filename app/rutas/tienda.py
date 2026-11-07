"""Panel del administrador de la tienda: pedidos y menús."""

import re

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse

from app.db import campos_foto, conectar, ejecutar, todos, uno
from app.pedidos import (
    ACTIVOS,
    ESTADOS,
    TIEMPOS,
    TRANSICIONES,
    agregar_items,
    leer_hora,
    mensaje_para_estudiante,
    menus_con_productos,
    notificar,
    texto_tiempo,
)
from app.fotos import leer_foto
from app.plantillas import mostrar_mensaje, render
from app.sesion import tienda_en_sesion
from app.validacion import Formulario

router = APIRouter(prefix="/tienda")

PRECIO_MAXIMO = 10_000_000


def leer_precio(texto: str) -> int | None:
    """Acepta '12500', '12.500' o '$ 12,500'. Devuelve None si no es válido."""
    limpio = re.sub(r"[\s$.,]", "", texto)
    if not limpio.isdigit():
        return None
    precio = int(limpio)
    return precio if 0 < precio <= PRECIO_MAXIMO else None


def validar_producto(nombre: str, descripcion: str, precio: str):
    """Devuelve ((nombre, descripcion, precio), None) o (None, mensaje de error)."""
    nombre, descripcion, valor = nombre.strip(), descripcion.strip(), leer_precio(precio)
    if not nombre or len(nombre) > 80:
        return None, "El nombre del producto es obligatorio (máximo 80 caracteres)."
    if len(descripcion) > 200:
        return None, "La descripción admite máximo 200 caracteres."
    if valor is None:
        return None, "Escribe un precio válido en pesos, por ejemplo 4500."
    return (nombre, descripcion, valor), None


# ---------- Pedidos ----------

@router.get("")
def ver_pedidos(request: Request, usuario: dict = Depends(tienda_en_sesion)):
    pedidos = agregar_items(todos(
        f"""
        SELECT p.id, p.estado, p.hora_recogida, p.total, p.creado_en, p.metodo_pago,
               p.tiempo_min, p.tiempo_max, p.aceptado_en, p.estudiante_id,
               u.nombre, u.apellido, u.telefono, {campos_foto("u")}
        FROM pedidos p
        LEFT JOIN usuarios u ON u.id = p.estudiante_id
        WHERE p.tienda_id = %s
        ORDER BY p.creado_en, p.id
        """,
        (usuario["tienda_id"],),
    ))
    columnas = {estado: [p for p in pedidos if p["estado"] == estado] for estado in ACTIVOS}
    finalizados = sorted(
        (p for p in pedidos if p["estado"] not in ACTIVOS),
        key=lambda p: p["creado_en"],
        reverse=True,
    )[:20]
    return render(
        request, "tienda/pedidos.html", columnas=columnas, finalizados=finalizados,
        en_curso=sum(len(c) for c in columnas.values()), transiciones=TRANSICIONES,
    )


@router.post("/disponibilidad")
def guardar_disponibilidad(
    request: Request,
    tiempo_min: str = Form(""),
    auto_aceptar: str = Form(""),
    hora_apertura: str = Form(""),
    hora_cierre: str = Form(""),
    usuario: dict = Depends(tienda_en_sesion),
):
    minutos = int(tiempo_min) if tiempo_min.isdigit() else None
    apertura, cierre = leer_hora(hora_apertura), leer_hora(hora_cierre)
    if minutos not in TIEMPOS:
        mostrar_mensaje(request, "Elige un tiempo de preparación válido.", "error")
    elif (apertura is None) != (cierre is None) or (apertura and apertura == cierre):
        mostrar_mensaje(request, "Escribe la hora de apertura y la de cierre (distintas), o deja las dos vacías.", "error")
    else:
        activar = auto_aceptar == "on"
        ejecutar(
            """
            UPDATE tiendas SET tiempo_min = %s, auto_aceptar = %s, hora_apertura = %s, hora_cierre = %s
            WHERE id = %s
            """,
            (minutos, activar, apertura, cierre, usuario["tienda_id"]),
        )
        modo = "se aceptan automáticamente" if activar else "los aceptas tú manualmente"
        horario = f" Horario: {apertura:%H:%M} a {cierre:%H:%M}." if apertura else ""
        mostrar_mensaje(request, f"Guardado: pedidos listos en {texto_tiempo(minutos)} y {modo}.{horario}")
    return RedirectResponse("/tienda", 303)


@router.post("/abrir-cerrar")
def abrir_cerrar(request: Request, usuario: dict = Depends(tienda_en_sesion)):
    fila = uno("UPDATE tiendas SET abierta = NOT abierta WHERE id = %s RETURNING abierta", (usuario["tienda_id"],))
    mostrar_mensaje(
        request,
        "Tu tienda está abierta y recibe pedidos." if fila["abierta"]
        else "Cerraste la tienda: los estudiantes no pueden hacer pedidos.",
    )
    return RedirectResponse("/tienda", 303)


@router.post("/pedidos/{pedido_id}/estado")
def cambiar_estado(
    request: Request,
    pedido_id: int,
    estado: str = Form(""),
    usuario: dict = Depends(tienda_en_sesion),
):
    with conectar() as conexion:
        pedido = conexion.execute(
            """
            SELECT estado, estudiante_id, tiempo_min
            FROM pedidos WHERE id = %s AND tienda_id = %s FOR UPDATE
            """,
            (pedido_id, usuario["tienda_id"]),
        ).fetchone()
        if pedido is None:
            mostrar_mensaje(request, "El pedido no existe.", "error")
        elif estado not in TRANSICIONES[pedido["estado"]]:
            mostrar_mensaje(request, "Ese cambio de estado no es posible.", "error")
        else:
            conexion.execute(
                """
                UPDATE pedidos
                SET estado = %s,
                    aceptado_en = CASE WHEN %s = 'aceptado' THEN now() ELSE aceptado_en END
                WHERE id = %s
                """,
                (estado, estado, pedido_id),
            )
            notificar(
                conexion,
                pedido["estudiante_id"],
                mensaje_para_estudiante(estado, pedido_id, usuario["tienda"], pedido["tiempo_min"]),
                pedido_id,
            )
            mostrar_mensaje(request, f"Pedido #{pedido_id}: {ESTADOS[estado]}.")
    return RedirectResponse("/tienda", 303)


# ---------- Menús y productos ----------

# Condición para que solo se modifiquen productos de la tienda en sesión.
DE_MI_TIENDA = "menu_id IN (SELECT id FROM menus WHERE tienda_id = %s)"


def resultado(request: Request, fila: dict | None, exito, error: str) -> RedirectResponse:
    """Si la consulta encontró la fila, muestra `exito` (texto o función de la fila); si no, `error`."""
    if fila:
        mostrar_mensaje(request, exito(fila) if callable(exito) else exito)
    else:
        mostrar_mensaje(request, error, "error")
    return RedirectResponse("/tienda/menu", 303)


@router.get("/menu")
def ver_menu(request: Request, usuario: dict = Depends(tienda_en_sesion)):
    return render(request, "tienda/menu.html", menus=menus_con_productos(usuario["tienda_id"]))


@router.post("/menus")
def crear_menu(request: Request, nombre: str = Form(""), usuario: dict = Depends(tienda_en_sesion)):
    f = Formulario(nombre=nombre)
    f.texto("nombre", "el nombre del menú", 60)
    if not f.valido:
        return resultado(request, None, "", f.errores["nombre"])
    fila = uno(
        "INSERT INTO menus (tienda_id, nombre) VALUES (%s, %s) RETURNING nombre",
        (usuario["tienda_id"], f["nombre"]),
    )
    return resultado(request, fila, lambda m: f"Menú «{m['nombre']}» creado.", "")


@router.post("/menus/{menu_id}/eliminar")
def eliminar_menu(request: Request, menu_id: int, usuario: dict = Depends(tienda_en_sesion)):
    fila = uno(
        "DELETE FROM menus WHERE id = %s AND tienda_id = %s RETURNING nombre",
        (menu_id, usuario["tienda_id"]),
    )
    return resultado(request, fila, lambda m: f"Menú «{m['nombre']}» eliminado.", "El menú no existe.")


@router.post("/menus/{menu_id}/productos")
def crear_producto(
    request: Request,
    menu_id: int,
    nombre: str = Form(""),
    descripcion: str = Form(""),
    precio: str = Form(""),
    usuario: dict = Depends(tienda_en_sesion),
):
    datos, error = validar_producto(nombre, descripcion, precio)
    if error:
        return resultado(request, None, "", error)
    fila = uno(
        """
        INSERT INTO productos (menu_id, nombre, descripcion, precio)
        SELECT id, %s, %s, %s FROM menus WHERE id = %s AND tienda_id = %s
        RETURNING nombre
        """,
        (*datos, menu_id, usuario["tienda_id"]),
    )
    return resultado(request, fila, lambda p: f"Producto «{p['nombre']}» agregado.", "El menú no existe.")


@router.post("/productos/{producto_id}/editar")
def editar_producto(
    request: Request,
    producto_id: int,
    nombre: str = Form(""),
    descripcion: str = Form(""),
    precio: str = Form(""),
    usuario: dict = Depends(tienda_en_sesion),
):
    datos, error = validar_producto(nombre, descripcion, precio)
    if error:
        return resultado(request, None, "", error)
    fila = uno(
        f"""
        UPDATE productos SET nombre = %s, descripcion = %s, precio = %s
        WHERE id = %s AND {DE_MI_TIENDA} RETURNING nombre
        """,
        (*datos, producto_id, usuario["tienda_id"]),
    )
    return resultado(request, fila, lambda p: f"Producto «{p['nombre']}» actualizado.", "El producto no existe.")


@router.post("/productos/{producto_id}/disponibilidad")
def cambiar_disponibilidad(request: Request, producto_id: int, usuario: dict = Depends(tienda_en_sesion)):
    fila = uno(
        f"""
        UPDATE productos SET disponible = NOT disponible
        WHERE id = %s AND {DE_MI_TIENDA} RETURNING nombre, disponible
        """,
        (producto_id, usuario["tienda_id"]),
    )
    return resultado(
        request, fila,
        lambda p: f"«{p['nombre']}» ahora está {'disponible' if p['disponible'] else 'agotado'}.",
        "El producto no existe.",
    )


@router.post("/productos/{producto_id}/eliminar")
def eliminar_producto(request: Request, producto_id: int, usuario: dict = Depends(tienda_en_sesion)):
    fila = uno(
        f"DELETE FROM productos WHERE id = %s AND {DE_MI_TIENDA} RETURNING nombre",
        (producto_id, usuario["tienda_id"]),
    )
    return resultado(request, fila, lambda p: f"Producto «{p['nombre']}» eliminado.", "El producto no existe.")


@router.post("/productos/{producto_id}/foto")
async def subir_foto_producto(
    request: Request, producto_id: int, foto: UploadFile = File(...), usuario: dict = Depends(tienda_en_sesion)
):
    jpeg, error = await leer_foto(foto, 480)
    if error:
        return resultado(request, None, "", error)
    fila = uno(
        f"UPDATE productos SET foto = %s, foto_actualizada = now() WHERE id = %s AND {DE_MI_TIENDA} RETURNING nombre",
        (jpeg, producto_id, usuario["tienda_id"]),
    )
    return resultado(request, fila, lambda p: f"Foto de «{p['nombre']}» actualizada.", "El producto no existe.")


@router.post("/productos/{producto_id}/foto/eliminar")
def eliminar_foto_producto(request: Request, producto_id: int, usuario: dict = Depends(tienda_en_sesion)):
    fila = uno(
        f"UPDATE productos SET foto = NULL, foto_actualizada = NULL WHERE id = %s AND {DE_MI_TIENDA} RETURNING nombre",
        (producto_id, usuario["tienda_id"]),
    )
    return resultado(request, fila, lambda p: f"Quitaste la foto de «{p['nombre']}».", "El producto no existe.")
