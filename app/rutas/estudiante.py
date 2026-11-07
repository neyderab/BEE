"""Vista del estudiante: tiendas de su universidad, pedidos."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.db import conectar
from app.pedidos import (
    RANGO_MINUTOS,
    agregar_items,
    mensaje_para_estudiante,
    menus_con_productos,
    notificar,
)
from app.plantillas import mostrar_mensaje, pesos, render
from app.sesion import estudiante_en_sesion

router = APIRouter(prefix="/estudiante")

CANTIDAD_MAXIMA = 20


def buscar_tienda(tienda_id: int, universidad_id: int) -> tuple[dict | None, int]:
    """Devuelve la tienda si es de la misma universidad del estudiante.

    Si no, devuelve (None, código HTTP): 404 si no existe y 403 si es de otra
    universidad.
    """
    with conectar() as conexion:
        tienda = conexion.execute(
            """
            SELECT t.id, t.nombre, t.tiempo_min, t.auto_aceptar,
                   t.usuario_id AS propietario_id,
                   u.universidad_id, un.nombre AS universidad
            FROM tiendas t
            JOIN usuarios u ON u.id = t.usuario_id
            JOIN universidades un ON un.id = u.universidad_id
            WHERE t.id = %s
            """,
            (tienda_id,),
        ).fetchone()
    if tienda is None:
        return None, 404
    if tienda["universidad_id"] != universidad_id:
        return None, 403
    return tienda, 200


def tienda_no_disponible(request: Request, codigo: int):
    texto = (
        "Esta tienda no pertenece a tu universidad. Solo puedes pedir en "
        "tiendas de tu universidad."
        if codigo == 403
        else "La tienda que buscas no existe."
    )
    return render(request, "error.html", status_code=codigo, texto=texto, volver="/estudiante")


@router.get("")
def ver_tiendas(request: Request, usuario: dict = Depends(estudiante_en_sesion)):
    with conectar() as conexion:
        tiendas = conexion.execute(
            """
            SELECT t.id, t.nombre, t.tiempo_min,
                   COUNT(p.id) FILTER (WHERE p.disponible) AS productos
            FROM tiendas t
            JOIN usuarios u ON u.id = t.usuario_id
            LEFT JOIN menus m ON m.tienda_id = t.id
            LEFT JOIN productos p ON p.menu_id = m.id
            WHERE u.universidad_id = %s
            GROUP BY t.id
            ORDER BY t.nombre
            """,
            (usuario["universidad_id"],),
        ).fetchall()
    return render(request, "estudiante/tiendas.html", tiendas=tiendas)


@router.get("/tiendas/{tienda_id}")
def ver_tienda(request: Request, tienda_id: int, usuario: dict = Depends(estudiante_en_sesion)):
    tienda, codigo = buscar_tienda(tienda_id, usuario["universidad_id"])
    if tienda is None:
        return tienda_no_disponible(request, codigo)
    return render(
        request,
        "estudiante/tienda.html",
        tienda=tienda,
        menus=menus_con_productos(tienda_id, solo_disponibles=True),
        cantidad_maxima=CANTIDAD_MAXIMA,
    )


@router.post("/tiendas/{tienda_id}/pedido")
async def crear_pedido(
    request: Request, tienda_id: int, usuario: dict = Depends(estudiante_en_sesion)
):
    # La regla principal: solo se puede pedir en tiendas de la misma universidad.
    tienda, codigo = buscar_tienda(tienda_id, usuario["universidad_id"])
    if tienda is None:
        return tienda_no_disponible(request, codigo)

    volver = RedirectResponse(f"/estudiante/tiendas/{tienda_id}", 303)
    formulario = await request.form()

    cantidades: dict[int, int] = {}
    for campo, valor in formulario.items():
        if not campo.startswith("cantidad_") or not str(valor).strip():
            continue
        try:
            producto_id, cantidad = int(campo.removeprefix("cantidad_")), int(valor)
        except ValueError:
            mostrar_mensaje(request, "Las cantidades deben ser números.", "error")
            return volver
        if not 0 <= cantidad <= CANTIDAD_MAXIMA:
            mostrar_mensaje(
                request, f"Puedes pedir entre 0 y {CANTIDAD_MAXIMA} unidades por producto.", "error"
            )
            return volver
        if cantidad:
            cantidades[producto_id] = cantidad

    if not cantidades:
        mostrar_mensaje(request, "Agrega al menos un producto a tu pedido.", "error")
        return volver

    with conectar() as conexion:
        productos = conexion.execute(
            """
            SELECT p.id, p.nombre, p.precio
            FROM productos p
            JOIN menus m ON m.id = p.menu_id
            WHERE p.id = ANY(%s) AND m.tienda_id = %s AND p.disponible
            """,
            (list(cantidades), tienda_id),
        ).fetchall()

        if len(productos) != len(cantidades):
            mostrar_mensaje(
                request,
                "Algún producto ya no está disponible. Revisa tu pedido.",
                "error",
            )
            return volver

        total = sum(p["precio"] * cantidades[p["id"]] for p in productos)
        # Se guarda el tiempo vigente: si la tienda lo cambia después, este
        # pedido conserva el que el estudiante vio al pedir.
        auto = tienda["auto_aceptar"]
        pedido = conexion.execute(
            """
            INSERT INTO pedidos
                (estudiante_id, tienda_id, total, tiempo_min, tiempo_max, estado, aceptado_en)
            VALUES (%s, %s, %s, %s, %s, %s, CASE WHEN %s THEN now() END)
            RETURNING id
            """,
            (
                usuario["id"],
                tienda_id,
                total,
                tienda["tiempo_min"],
                tienda["tiempo_min"] + RANGO_MINUTOS,
                "aceptado" if auto else "pendiente",
                auto,
            ),
        ).fetchone()
        with conexion.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO pedido_items
                    (pedido_id, producto_id, nombre_producto, precio_unitario, cantidad)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [
                    (pedido["id"], p["id"], p["nombre"], p["precio"], cantidades[p["id"]])
                    for p in productos
                ],
            )

        cliente = f"{usuario['nombre']} {usuario['apellido']}".strip()
        notificar(
            conexion,
            tienda["propietario_id"],
            f"Nuevo pedido #{pedido['id']} de {cliente} por {pesos(total)}"
            + (" (aceptado automáticamente)." if auto else ". Acéptalo para empezar."),
            pedido["id"],
        )
        if auto:
            notificar(
                conexion,
                usuario["id"],
                mensaje_para_estudiante("aceptado", pedido["id"], tienda["nombre"], tienda["tiempo_min"]),
                pedido["id"],
            )

    if auto:
        aviso = f"¡{tienda['nombre']} aceptó tu pedido #{pedido['id']}!"
    else:
        aviso = f"Pedido #{pedido['id']} enviado. Te avisaremos cuando {tienda['nombre']} lo acepte."
    mostrar_mensaje(request, aviso)
    return RedirectResponse("/estudiante/pedidos", 303)


@router.get("/pedidos")
def ver_mis_pedidos(request: Request, usuario: dict = Depends(estudiante_en_sesion)):
    with conectar() as conexion:
        pedidos = conexion.execute(
            """
            SELECT p.id, p.estado, p.hora_recogida, p.total, p.creado_en,
                   p.tiempo_min, p.tiempo_max, p.aceptado_en,
                   t.nombre AS tienda
            FROM pedidos p
            JOIN tiendas t ON t.id = p.tienda_id
            WHERE p.estudiante_id = %s
            ORDER BY p.creado_en DESC
            LIMIT 30
            """,
            (usuario["id"],),
        ).fetchall()
    return render(
        request, "estudiante/pedidos.html", pedidos=agregar_items(pedidos)
    )
