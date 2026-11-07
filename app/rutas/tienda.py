"""Panel del administrador de la tienda: pedidos y menús."""

import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.db import conectar
from app.pedidos import ACTIVOS, ESTADOS, TRANSICIONES, agregar_items, menus_con_productos
from app.plantillas import mostrar_mensaje, render
from app.sesion import tienda_en_sesion

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
    nombre, descripcion = nombre.strip(), descripcion.strip()
    if not nombre or len(nombre) > 80:
        return None, "El nombre del producto es obligatorio (máximo 80 caracteres)."
    if len(descripcion) > 200:
        return None, "La descripción admite máximo 200 caracteres."
    valor = leer_precio(precio)
    if valor is None:
        return None, "Escribe un precio válido en pesos, por ejemplo 4500."
    return (nombre, descripcion, valor), None


def volver_al_menu() -> RedirectResponse:
    return RedirectResponse("/tienda/menu", 303)


# ---------- Pedidos ----------

@router.get("")
def ver_pedidos(request: Request, usuario: dict = Depends(tienda_en_sesion)):
    with conectar() as conexion:
        pedidos = conexion.execute(
            """
            SELECT p.id, p.estado, p.hora_recogida, p.total, p.creado_en,
                   u.nombre, u.apellido, u.telefono
            FROM pedidos p
            JOIN usuarios u ON u.id = p.estudiante_id
            WHERE p.tienda_id = %s
            ORDER BY p.hora_recogida, p.id
            """,
            (usuario["tienda_id"],),
        ).fetchall()
    agregar_items(pedidos)
    activos = [p for p in pedidos if p["estado"] in ACTIVOS]
    finalizados = sorted(
        (p for p in pedidos if p["estado"] not in ACTIVOS),
        key=lambda p: p["creado_en"],
        reverse=True,
    )[:20]
    return render(
        request,
        "tienda/pedidos.html",
        activos=activos,
        finalizados=finalizados,
        estados=ESTADOS,
        transiciones=TRANSICIONES,
    )


@router.post("/pedidos/{pedido_id}/estado")
def cambiar_estado(
    request: Request,
    pedido_id: int,
    estado: str = Form(""),
    usuario: dict = Depends(tienda_en_sesion),
):
    with conectar() as conexion:
        pedido = conexion.execute(
            "SELECT estado FROM pedidos WHERE id = %s AND tienda_id = %s FOR UPDATE",
            (pedido_id, usuario["tienda_id"]),
        ).fetchone()
        if pedido is None:
            mostrar_mensaje(request, "El pedido no existe.", "error")
        elif estado not in TRANSICIONES[pedido["estado"]]:
            mostrar_mensaje(request, "Ese cambio de estado no es posible.", "error")
        else:
            conexion.execute(
                "UPDATE pedidos SET estado = %s WHERE id = %s", (estado, pedido_id)
            )
            mostrar_mensaje(request, f"Pedido #{pedido_id}: {ESTADOS[estado]}.")
    return RedirectResponse("/tienda", 303)


# ---------- Menús y productos ----------

@router.get("/menu")
def ver_menu(request: Request, usuario: dict = Depends(tienda_en_sesion)):
    return render(request, "tienda/menu.html", menus=menus_con_productos(usuario["tienda_id"]))


@router.post("/menus")
def crear_menu(
    request: Request, nombre: str = Form(""), usuario: dict = Depends(tienda_en_sesion)
):
    nombre = nombre.strip()
    if not nombre or len(nombre) > 60:
        mostrar_mensaje(request, "El nombre del menú es obligatorio (máximo 60 caracteres).", "error")
        return volver_al_menu()
    with conectar() as conexion:
        conexion.execute(
            "INSERT INTO menus (tienda_id, nombre) VALUES (%s, %s)",
            (usuario["tienda_id"], nombre),
        )
    mostrar_mensaje(request, f"Menú «{nombre}» creado.")
    return volver_al_menu()


@router.post("/menus/{menu_id}/eliminar")
def eliminar_menu(request: Request, menu_id: int, usuario: dict = Depends(tienda_en_sesion)):
    with conectar() as conexion:
        borrado = conexion.execute(
            "DELETE FROM menus WHERE id = %s AND tienda_id = %s RETURNING nombre",
            (menu_id, usuario["tienda_id"]),
        ).fetchone()
    if borrado:
        mostrar_mensaje(request, f"Menú «{borrado['nombre']}» eliminado.")
    else:
        mostrar_mensaje(request, "El menú no existe.", "error")
    return volver_al_menu()


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
        mostrar_mensaje(request, error, "error")
        return volver_al_menu()
    with conectar() as conexion:
        creado = conexion.execute(
            """
            INSERT INTO productos (menu_id, nombre, descripcion, precio)
            SELECT id, %s, %s, %s FROM menus WHERE id = %s AND tienda_id = %s
            RETURNING id
            """,
            (*datos, menu_id, usuario["tienda_id"]),
        ).fetchone()
    if creado:
        mostrar_mensaje(request, f"Producto «{datos[0]}» agregado.")
    else:
        mostrar_mensaje(request, "El menú no existe.", "error")
    return volver_al_menu()


# Condición para que solo se modifiquen productos de la tienda en sesión.
DE_MI_TIENDA = "menu_id IN (SELECT id FROM menus WHERE tienda_id = %s)"


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
        mostrar_mensaje(request, error, "error")
        return volver_al_menu()
    with conectar() as conexion:
        editado = conexion.execute(
            f"""
            UPDATE productos SET nombre = %s, descripcion = %s, precio = %s
            WHERE id = %s AND {DE_MI_TIENDA}
            RETURNING id
            """,
            (*datos, producto_id, usuario["tienda_id"]),
        ).fetchone()
    if editado:
        mostrar_mensaje(request, f"Producto «{datos[0]}» actualizado.")
    else:
        mostrar_mensaje(request, "El producto no existe.", "error")
    return volver_al_menu()


@router.post("/productos/{producto_id}/disponibilidad")
def cambiar_disponibilidad(
    request: Request, producto_id: int, usuario: dict = Depends(tienda_en_sesion)
):
    with conectar() as conexion:
        producto = conexion.execute(
            f"""
            UPDATE productos SET disponible = NOT disponible
            WHERE id = %s AND {DE_MI_TIENDA}
            RETURNING nombre, disponible
            """,
            (producto_id, usuario["tienda_id"]),
        ).fetchone()
    if producto:
        estado = "disponible" if producto["disponible"] else "agotado"
        mostrar_mensaje(request, f"«{producto['nombre']}» ahora está {estado}.")
    else:
        mostrar_mensaje(request, "El producto no existe.", "error")
    return volver_al_menu()


@router.post("/productos/{producto_id}/eliminar")
def eliminar_producto(
    request: Request, producto_id: int, usuario: dict = Depends(tienda_en_sesion)
):
    with conectar() as conexion:
        borrado = conexion.execute(
            f"DELETE FROM productos WHERE id = %s AND {DE_MI_TIENDA} RETURNING nombre",
            (producto_id, usuario["tienda_id"]),
        ).fetchone()
    if borrado:
        mostrar_mensaje(request, f"Producto «{borrado['nombre']}» eliminado.")
    else:
        mostrar_mensaje(request, "El producto no existe.", "error")
    return volver_al_menu()
