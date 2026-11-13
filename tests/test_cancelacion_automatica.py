"""Un pedido aceptado que pasa 30 minutos sin cambiar de estado se cancela solo."""

import pytest

from app.modelos import pedidos
from app.modelos.base_datos import conectar, uno
from tests.conftest import entrar, registrar


@pytest.fixture
def pedido_aceptado(cliente, nuevo_cliente):
    registrar(cliente, "3100000001", rol="Tienda", nombre_tienda="Café USB")
    tienda = nuevo_cliente()
    entrar(tienda, "3100000001")
    tienda.post("/tienda/menus", data={"nombre": "Bebidas"})
    menu_id = uno("SELECT id FROM menus")["id"]
    tienda.post(f"/tienda/menus/{menu_id}/productos", data={"nombre": "Tinto", "precio": "1500"})
    registrar(cliente, "3200000001")
    alumno = nuevo_cliente()
    entrar(alumno, "3200000001")
    ids = uno("SELECT t.id AS tienda, (SELECT id FROM productos) AS producto FROM tiendas t")
    alumno.post(f"/estudiante/tiendas/{ids['tienda']}/pedido", data={f"cantidad_{ids['producto']}": "1"})
    pedido_id = uno("SELECT id FROM pedidos")["id"]
    tienda.post(f"/tienda/pedidos/{pedido_id}/estado", data={"estado": "aceptado"})
    assert uno("SELECT estado FROM pedidos")["estado"] == "aceptado"
    return tienda, alumno, pedido_id


def envejecer(pedido_id, minutos):
    with conectar() as conexion:
        conexion.execute(
            "UPDATE pedidos SET aceptado_en = now() - make_interval(mins => %s) WHERE id = %s", (minutos, pedido_id)
        )


def test_aceptado_hace_poco_no_se_cancela(pedido_aceptado):
    _, alumno, pedido_id = pedido_aceptado
    envejecer(pedido_id, 29)
    assert pedidos.cancelar_vencidos() == 0
    assert uno("SELECT estado FROM pedidos")["estado"] == "aceptado"


def test_aceptado_sin_avanzar_30_minutos_se_cancela_y_avisa(pedido_aceptado):
    tienda, alumno, pedido_id = pedido_aceptado
    envejecer(pedido_id, 31)
    assert pedidos.cancelar_vencidos() == 1
    assert uno("SELECT estado FROM pedidos")["estado"] == "cancelado"
    avisos = [f["texto"] for f in pedidos.todos("SELECT texto FROM notificaciones ORDER BY id")]
    assert any("se canceló porque la tienda no lo empezó a preparar" in t for t in avisos)
    assert any("se canceló solo" in t for t in avisos)
    assert pedidos.cancelar_vencidos() == 0  # No se cancela ni avisa dos veces.


def test_se_cancela_al_abrir_la_lista_aunque_el_servidor_estuviera_dormido(pedido_aceptado):
    _, alumno, pedido_id = pedido_aceptado
    envejecer(pedido_id, 45)
    assert "Cancelado" in alumno.get("/estudiante/pedidos").text
    assert uno("SELECT estado FROM pedidos")["estado"] == "cancelado"


def test_pedido_en_preparacion_no_se_cancela(pedido_aceptado):
    tienda, _, pedido_id = pedido_aceptado
    tienda.post(f"/tienda/pedidos/{pedido_id}/estado", data={"estado": "preparando"})
    envejecer(pedido_id, 120)
    assert pedidos.cancelar_vencidos() == 0
    assert uno("SELECT estado FROM pedidos")["estado"] == "preparando"


def test_la_tienda_ve_hasta_cuando_tiene_para_prepararlo(pedido_aceptado):
    tienda, _, _ = pedido_aceptado
    assert "se cancelará automáticamente" in tienda.get("/tienda").text
