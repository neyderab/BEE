"""Controlador de la tienda: pedidos, disponibilidad, menús y productos."""

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse

from app.controladores.dependencias import tienda_en_sesion
from app.modelos import menus, pedidos, tiendas
from app.modelos.pedidos import ACTIVOS, ESTADOS, TRANSICIONES, PedidoInvalido
from app.modelos.tiendas import TIEMPOS, leer_hora, texto_tiempo
from app.servicios.fotos import leer_foto
from app.servicios.validacion import Formulario
from app.vistas.plantillas import mostrar_mensaje, render

router = APIRouter(prefix="/tienda")


def volver_al_panel() -> RedirectResponse:
    return RedirectResponse("/tienda", 303)


# ---------- Pedidos ----------

@router.get("")
def ver_pedidos(request: Request, usuario: dict = Depends(tienda_en_sesion)):
    lista = pedidos.de_tienda(usuario["tienda_id"])
    columnas = {estado: [p for p in lista if p["estado"] == estado] for estado in ACTIVOS}
    finalizados = sorted((p for p in lista if p["estado"] not in ACTIVOS), key=lambda p: p["creado_en"], reverse=True)[:20]
    return render(
        request, "tienda/pedidos.html", columnas=columnas, finalizados=finalizados,
        en_curso=sum(len(c) for c in columnas.values()), transiciones=TRANSICIONES,
    )


@router.post("/pedidos/{pedido_id}/estado")
def cambiar_estado(request: Request, pedido_id: int, estado: str = Form(""), usuario: dict = Depends(tienda_en_sesion)):
    try:
        pedidos.cambiar_estado(usuario, pedido_id, estado)
        mostrar_mensaje(request, f"Pedido #{pedido_id}: {ESTADOS[estado]}.")
    except PedidoInvalido as motivo:
        mostrar_mensaje(request, str(motivo), "error")
    return volver_al_panel()


@router.post("/entregar")
def entregar_con_codigo(request: Request, codigo: str = Form(""), usuario: dict = Depends(tienda_en_sesion)):
    """Entrega el pedido listo cuyo código de recogida dice el estudiante."""
    pedido = pedidos.entregar_con_codigo(usuario, codigo)
    if pedido:
        quien = f" a {pedido['nombre']}" if pedido["nombre"] else ""
        mostrar_mensaje(request, f"✅ Pedido #{pedido['id']} entregado{quien}.")
    else:
        mostrar_mensaje(request, "Ese código no corresponde a ningún pedido listo. Pídele al estudiante que lo revise.", "error")
    return volver_al_panel()


# ---------- Disponibilidad ----------

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
        tiendas.guardar_disponibilidad(usuario["tienda_id"], minutos, activar, apertura, cierre)
        modo = "se aceptan automáticamente" if activar else "los aceptas tú manualmente"
        horario = f" Horario: {apertura:%H:%M} a {cierre:%H:%M}." if apertura else ""
        mostrar_mensaje(request, f"Guardado: pedidos listos en {texto_tiempo(minutos)} y {modo}.{horario}")
    return volver_al_panel()


@router.post("/abrir-cerrar")
def abrir_cerrar(request: Request, usuario: dict = Depends(tienda_en_sesion)):
    abierta = tiendas.alternar_abierta(usuario["tienda_id"])
    mostrar_mensaje(
        request,
        "Tu tienda está abierta y recibe pedidos." if abierta else "Cerraste la tienda: los estudiantes no pueden hacer pedidos.",
    )
    return volver_al_panel()


# ---------- Menús y productos ----------

def resultado(request: Request, fila: dict | None, exito, error: str) -> RedirectResponse:
    """Si el modelo encontró la fila, muestra `exito` (texto o función de la fila); si no, `error`."""
    if fila:
        mostrar_mensaje(request, exito(fila) if callable(exito) else exito)
    else:
        mostrar_mensaje(request, error, "error")
    return RedirectResponse("/tienda/menu", 303)


@router.get("/menu")
def ver_menu(request: Request, usuario: dict = Depends(tienda_en_sesion)):
    return render(request, "tienda/menu.html", menus=menus.menus_con_productos(usuario["tienda_id"]))


@router.post("/menus")
def crear_menu(request: Request, nombre: str = Form(""), usuario: dict = Depends(tienda_en_sesion)):
    f = Formulario(nombre=nombre)
    f.texto("nombre", "el nombre del menú", 60)
    if not f.valido:
        return resultado(request, None, "", f.errores["nombre"])
    fila = menus.crear_menu(usuario["tienda_id"], f["nombre"])
    return resultado(request, fila, lambda m: f"Menú «{m['nombre']}» creado.", "")


@router.post("/menus/{menu_id}/eliminar")
def eliminar_menu(request: Request, menu_id: int, usuario: dict = Depends(tienda_en_sesion)):
    fila = menus.eliminar_menu(usuario["tienda_id"], menu_id)
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
    datos, error = menus.validar_producto(nombre, descripcion, precio)
    if error:
        return resultado(request, None, "", error)
    fila = menus.crear_producto(usuario["tienda_id"], menu_id, *datos)
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
    datos, error = menus.validar_producto(nombre, descripcion, precio)
    if error:
        return resultado(request, None, "", error)
    fila = menus.editar_producto(usuario["tienda_id"], producto_id, *datos)
    return resultado(request, fila, lambda p: f"Producto «{p['nombre']}» actualizado.", "El producto no existe.")


@router.post("/productos/{producto_id}/disponibilidad")
def cambiar_disponibilidad(request: Request, producto_id: int, usuario: dict = Depends(tienda_en_sesion)):
    fila = menus.alternar_disponible(usuario["tienda_id"], producto_id)
    return resultado(
        request, fila,
        lambda p: f"«{p['nombre']}» ahora está {'disponible' if p['disponible'] else 'agotado'}.",
        "El producto no existe.",
    )


@router.post("/productos/{producto_id}/eliminar")
def eliminar_producto(request: Request, producto_id: int, usuario: dict = Depends(tienda_en_sesion)):
    fila = menus.eliminar_producto(usuario["tienda_id"], producto_id)
    return resultado(request, fila, lambda p: f"Producto «{p['nombre']}» eliminado.", "El producto no existe.")


@router.post("/productos/{producto_id}/foto")
async def subir_foto_producto(
    request: Request, producto_id: int, foto: UploadFile = File(...), usuario: dict = Depends(tienda_en_sesion)
):
    jpeg, error = await leer_foto(foto, 480)
    if error:
        return resultado(request, None, "", error)
    fila = menus.guardar_foto_producto(usuario["tienda_id"], producto_id, jpeg)
    return resultado(request, fila, lambda p: f"Foto de «{p['nombre']}» actualizada.", "El producto no existe.")


@router.post("/productos/{producto_id}/foto/eliminar")
def eliminar_foto_producto(request: Request, producto_id: int, usuario: dict = Depends(tienda_en_sesion)):
    fila = menus.guardar_foto_producto(usuario["tienda_id"], producto_id, None)
    return resultado(request, fila, lambda p: f"Quitaste la foto de «{p['nombre']}».", "El producto no existe.")
