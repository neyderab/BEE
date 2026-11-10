import pytest

from app.modelos.base_datos import conectar
from tests.conftest import ANDES, USB, entrar, registrar


@pytest.fixture
def tienda_usb(cliente, nuevo_cliente):
    """Tienda en San Buenaventura con un menú y dos productos."""
    registrar(cliente, "3100000001", rol="Tienda", nombre_tienda="Café USB")
    tienda = nuevo_cliente()
    entrar(tienda, "3100000001")
    tienda.post("/tienda/menus", data={"nombre": "Desayunos"})
    with conectar() as conexion:
        menu_id = conexion.execute("SELECT id FROM menus").fetchone()["id"]
    tienda.post(f"/tienda/menus/{menu_id}/productos",
                data={"nombre": "Empanada", "descripcion": "De carne", "precio": "2.500"})
    tienda.post(f"/tienda/menus/{menu_id}/productos", data={"nombre": "Tinto", "precio": "1500"})
    return tienda


def producto(nombre):
    with conectar() as conexion:
        return conexion.execute("SELECT * FROM productos WHERE nombre = %s", (nombre,)).fetchone()


def estudiante(cliente, nuevo_cliente, telefono, universidad):
    registrar(cliente, telefono, universidad=universidad)
    c = nuevo_cliente()
    entrar(c, telefono)
    return c


def test_tienda_crea_menu_y_productos_con_precio(tienda_usb):
    pagina = tienda_usb.get("/tienda/menu").text
    assert "Desayunos" in pagina
    assert "Empanada" in pagina and "$2.500" in pagina
    assert producto("Tinto")["precio"] == 1500


def test_tienda_edita_precio_y_disponibilidad(tienda_usb):
    tinto = producto("Tinto")
    tienda_usb.post(f"/tienda/productos/{tinto['id']}/editar",
                    data={"nombre": "Tinto grande", "descripcion": "", "precio": "2000"})
    tienda_usb.post(f"/tienda/productos/{tinto['id']}/disponibilidad")
    actualizado = producto("Tinto grande")
    assert actualizado["precio"] == 2000
    assert actualizado["disponible"] is False


def test_precio_invalido_no_se_guarda(tienda_usb):
    with conectar() as conexion:
        menu_id = conexion.execute("SELECT id FROM menus").fetchone()["id"]
    respuesta = tienda_usb.post(f"/tienda/menus/{menu_id}/productos",
                                data={"nombre": "Gratis", "precio": "-5"})
    assert "precio válido" in respuesta.text
    assert producto("Gratis") is None


def test_tienda_no_modifica_productos_de_otra_tienda(cliente, nuevo_cliente, tienda_usb):
    registrar(cliente, "3100000002", rol="Tienda", nombre_tienda="Otra")
    otra = nuevo_cliente()
    entrar(otra, "3100000002")
    tinto = producto("Tinto")
    otra.post(f"/tienda/productos/{tinto['id']}/editar", data={"nombre": "Hackeado", "precio": "1"})
    otra.post(f"/tienda/productos/{tinto['id']}/eliminar")
    assert producto("Tinto")["precio"] == 1500


def test_estudiante_solo_ve_tiendas_de_su_universidad(cliente, nuevo_cliente, tienda_usb):
    de_usb = estudiante(cliente, nuevo_cliente, "3200000001", USB)
    de_andes = estudiante(cliente, nuevo_cliente, "3200000002", ANDES)
    assert "Café USB" in de_usb.get("/estudiante").text
    assert "Café USB" not in de_andes.get("/estudiante").text


def test_flujo_completo_de_pedido(cliente, nuevo_cliente, tienda_usb):
    alumno = estudiante(cliente, nuevo_cliente, "3200000001", USB)
    empanada, tinto = producto("Empanada"), producto("Tinto")
    with conectar() as conexion:
        tienda_id = conexion.execute("SELECT id FROM tiendas").fetchone()["id"]

    respuesta = alumno.post(
        f"/estudiante/tiendas/{tienda_id}/pedido",
        data={f"cantidad_{empanada['id']}": "2", f"cantidad_{tinto['id']}": "1"},
    )
    assert str(respuesta.url).endswith("/estudiante/pedidos")
    assert "$6.500" in respuesta.text  # 2 × 2.500 + 1.500
    assert "Esperando confirmación" in respuesta.text

    panel = tienda_usb.get("/tienda").text
    assert "2 × Empanada" in panel and "Ana Pérez" in panel and "Aceptar pedido" in panel

    with conectar() as conexion:
        pedido_id = conexion.execute("SELECT id FROM pedidos").fetchone()["id"]
    for estado in ("aceptado", "preparando", "listo"):
        tienda_usb.post(f"/tienda/pedidos/{pedido_id}/estado", data={"estado": estado})
    assert "Listo para recoger" in alumno.get("/estudiante/pedidos").text

    # No se puede saltar de "listo" a "cancelado".
    tienda_usb.post(f"/tienda/pedidos/{pedido_id}/estado", data={"estado": "cancelado"})
    with conectar() as conexion:
        assert conexion.execute("SELECT estado FROM pedidos").fetchone()["estado"] == "listo"


def test_estudiante_de_otra_universidad_no_puede_pedir(cliente, nuevo_cliente, tienda_usb):
    alumno = estudiante(cliente, nuevo_cliente, "3200000002", ANDES)
    with conectar() as conexion:
        tienda_id = conexion.execute("SELECT id FROM tiendas").fetchone()["id"]

    assert alumno.get(f"/estudiante/tiendas/{tienda_id}").status_code == 403
    respuesta = alumno.post(
        f"/estudiante/tiendas/{tienda_id}/pedido",
        data={f"cantidad_{producto('Tinto')['id']}": "1"},
    )
    assert respuesta.status_code == 403
    assert "no pertenece a tu universidad" in respuesta.text
    with conectar() as conexion:
        assert conexion.execute("SELECT COUNT(*) AS n FROM pedidos").fetchone()["n"] == 0


def test_no_se_pide_un_producto_agotado(cliente, nuevo_cliente, tienda_usb):
    alumno = estudiante(cliente, nuevo_cliente, "3200000001", USB)
    tinto = producto("Tinto")
    tienda_usb.post(f"/tienda/productos/{tinto['id']}/disponibilidad")
    with conectar() as conexion:
        tienda_id = conexion.execute("SELECT id FROM tiendas").fetchone()["id"]
    respuesta = alumno.post(f"/estudiante/tiendas/{tienda_id}/pedido",
                            data={f"cantidad_{tinto['id']}": "1"})
    assert "ya no está disponible" in respuesta.text
    with conectar() as conexion:
        assert conexion.execute("SELECT COUNT(*) AS n FROM pedidos").fetchone()["n"] == 0
