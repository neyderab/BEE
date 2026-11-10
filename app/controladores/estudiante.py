"""Controlador del estudiante: tiendas de su universidad, pedir, seguir y cancelar pedidos."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.controladores.dependencias import estudiante_en_sesion
from app.modelos import menus, pedidos, tiendas
from app.modelos.pedidos import CANTIDAD_MAXIMA, METODO_PREDETERMINADO, PedidoInvalido
from app.vistas.plantillas import mostrar_mensaje, render

router = APIRouter(prefix="/estudiante")


def tienda_de_mi_universidad(request: Request, tienda_id: int, usuario: dict):
    """La tienda, o la página de error si no existe (404) o es de otra universidad (403)."""
    tienda = tiendas.buscar(tienda_id)
    if tienda and tienda["universidad_id"] == usuario["universidad_id"]:
        return tienda, None
    if tienda is None:
        texto, codigo = "La tienda que buscas no existe.", 404
    else:
        texto, codigo = "Esta tienda no pertenece a tu universidad. Solo puedes pedir en tiendas de tu universidad.", 403
    return None, render(request, "errores/error.html", status_code=codigo, texto=texto, volver="/estudiante")


def leer_cantidades(formulario) -> dict[int, int]:
    """{producto_id: cantidad} a partir de los campos cantidad_<id>. Lanza PedidoInvalido."""
    cantidades = {}
    for campo, valor in formulario.items():
        if not campo.startswith("cantidad_") or not str(valor).strip():
            continue
        try:
            producto_id, cantidad = int(campo.removeprefix("cantidad_")), int(valor)
        except ValueError as error:
            raise PedidoInvalido("Las cantidades deben ser números.") from error
        if not 0 <= cantidad <= CANTIDAD_MAXIMA:
            raise PedidoInvalido(f"Puedes pedir entre 0 y {CANTIDAD_MAXIMA} unidades por producto.")
        if cantidad:
            cantidades[producto_id] = cantidad
    return cantidades


@router.get("")
def ver_tiendas(request: Request, usuario: dict = Depends(estudiante_en_sesion)):
    return render(
        request, "estudiante/tiendas.html", seccion="tiendas",
        tiendas=tiendas.listar_de_universidad(usuario["universidad_id"]),
    )


@router.get("/tiendas/{tienda_id}")
def ver_tienda(request: Request, tienda_id: int, repetir: int | None = None, usuario: dict = Depends(estudiante_en_sesion)):
    tienda, error = tienda_de_mi_universidad(request, tienda_id, usuario)
    if error:
        return error
    menu = menus.menus_con_productos(tienda_id, solo_disponibles=True)

    # «Pedir de nuevo»: llena el carrito con los productos de un pedido anterior.
    cantidades, faltantes = {}, []
    if repetir:
        disponibles = {p["id"] for m in menu for p in m["productos"]}
        for item in pedidos.items_para_repetir(repetir, usuario["id"], tienda_id):
            if item["producto_id"] in disponibles:
                cantidades[item["producto_id"]] = item["cantidad"]
            else:
                faltantes.append(item["nombre_producto"])

    return render(
        request, "estudiante/tienda.html", seccion="tiendas", tienda=tienda, menus=menu,
        cantidad_maxima=CANTIDAD_MAXIMA, cantidades=cantidades, faltantes=faltantes,
    )


@router.post("/tiendas/{tienda_id}/pedido")
async def crear_pedido(request: Request, tienda_id: int, usuario: dict = Depends(estudiante_en_sesion)):
    # La regla principal: solo se puede pedir en tiendas de la misma universidad.
    tienda, error = tienda_de_mi_universidad(request, tienda_id, usuario)
    if error:
        return error
    formulario = await request.form()
    try:
        pedido = pedidos.crear(
            usuario, tienda, leer_cantidades(formulario),
            str(formulario.get("metodo_pago") or METODO_PREDETERMINADO),
        )
    except PedidoInvalido as motivo:
        mostrar_mensaje(request, str(motivo), "error")
        return RedirectResponse(f"/estudiante/tiendas/{tienda_id}", 303)

    if pedido["aceptado"]:
        mostrar_mensaje(request, f"¡{tienda['nombre']} aceptó tu pedido #{pedido['id']}!")
    else:
        mostrar_mensaje(request, f"Pedido #{pedido['id']} enviado. Te avisaremos cuando {tienda['nombre']} lo acepte.")
    return RedirectResponse("/estudiante/pedidos", 303)


@router.get("/pedidos")
def ver_mis_pedidos(request: Request, usuario: dict = Depends(estudiante_en_sesion)):
    return render(request, "estudiante/pedidos.html", seccion="pedidos", pedidos=pedidos.de_estudiante(usuario["id"]))


@router.post("/pedidos/{pedido_id}/cancelar")
def cancelar_pedido(request: Request, pedido_id: int, usuario: dict = Depends(estudiante_en_sesion)):
    if pedidos.cancelar_por_estudiante(usuario, pedido_id):
        mostrar_mensaje(request, f"Cancelaste el pedido #{pedido_id}.")
    else:
        mostrar_mensaje(request, "Ese pedido ya no se puede cancelar: la tienda ya lo aceptó.", "error")
    return RedirectResponse("/estudiante/pedidos", 303)
