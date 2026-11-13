"""Horario de tiendas, pago, cancelar, fotos de productos, repetir pedido, CSRF y migraciones."""

import io
from datetime import datetime, time

import pytest
from PIL import Image

from app.modelos.base_datos import uno
from app.config import ZONA_HORARIA
from app.modelos.tiendas import tienda_abierta
from tests.conftest import ANDES, USB, entrar, registrar


@pytest.fixture
def escenario(cliente, nuevo_cliente):
    """Tienda en San Buenaventura con Tinto y Empanada, y un estudiante de la misma universidad."""
    registrar(cliente, "3100000001", rol="Tienda", nombre_tienda="Café USB")
    tienda = nuevo_cliente()
    entrar(tienda, "3100000001")
    tienda.post("/tienda/menus", data={"nombre": "Bebidas"})
    menu_id = uno("SELECT id FROM menus")["id"]
    for nombre, precio in (("Tinto", "1500"), ("Empanada", "2500")):
        tienda.post(f"/tienda/menus/{menu_id}/productos", data={"nombre": nombre, "precio": precio})
    registrar(cliente, "3200000001", universidad=USB)
    alumno = nuevo_cliente()
    entrar(alumno, "3200000001")
    return tienda, alumno


def ids():
    return uno(
        "SELECT t.id AS tienda, (SELECT id FROM productos WHERE nombre = 'Tinto') AS tinto, "
        "(SELECT id FROM productos WHERE nombre = 'Empanada') AS empanada FROM tiendas t"
    )


def pedir(alumno, **extra):
    i = ids()
    return alumno.post(f"/estudiante/tiendas/{i['tienda']}/pedido", data={f"cantidad_{i['tinto']}": "2", **extra})


def contar_pedidos():
    return uno("SELECT COUNT(*) AS n FROM pedidos")["n"]


def imagen():
    salida = io.BytesIO()
    Image.new("RGB", (900, 600), (200, 120, 40)).save(salida, "PNG")
    return salida.getvalue()


# ---------- Horario de la tienda ----------

def test_tienda_cerrada_no_recibe_pedidos(escenario):
    tienda, alumno = escenario
    respuesta = tienda.post("/tienda/abrir-cerrar")
    assert "Cerraste la tienda" in respuesta.text
    assert "Cerrada" in alumno.get("/estudiante").text

    respuesta = pedir(alumno)
    assert "está cerrada" in respuesta.text
    assert contar_pedidos() == 0

    tienda.post("/tienda/abrir-cerrar")
    pedir(alumno)
    assert contar_pedidos() == 1


def test_horario_fijo(escenario):
    tienda, _ = escenario
    tienda.post("/tienda/disponibilidad", data={"tiempo_min": "10", "hora_apertura": "07:00", "hora_cierre": "18:30"})
    fila = uno("SELECT hora_apertura, hora_cierre FROM tiendas")
    assert (fila["hora_apertura"], fila["hora_cierre"]) == (time(7, 0), time(18, 30))

    respuesta = tienda.post("/tienda/disponibilidad", data={"tiempo_min": "10", "hora_apertura": "07:00"})
    assert "apertura y la de cierre" in respuesta.text


@pytest.mark.parametrize(
    "apertura, cierre, ahora, esperado",
    [
        (None, None, "03:00", True),         # Sin horario: depende solo del interruptor.
        ("07:00", "18:00", "06:59", False),
        ("07:00", "18:00", "07:00", True),
        ("07:00", "18:00", "18:00", False),
        ("20:00", "02:00", "23:30", True),    # Horario que pasa la medianoche.
        ("20:00", "02:00", "01:59", True),
        ("20:00", "02:00", "12:00", False),
    ],
)
def test_calculo_de_horario(apertura, cierre, ahora, esperado):
    tienda = {
        "abierta": True,
        "hora_apertura": time.fromisoformat(apertura) if apertura else None,
        "hora_cierre": time.fromisoformat(cierre) if cierre else None,
    }
    momento = datetime.combine(datetime(2026, 11, 7), time.fromisoformat(ahora), ZONA_HORARIA)
    assert tienda_abierta(tienda, momento) is esperado
    assert tienda_abierta({**tienda, "abierta": False}, momento) is False


# ---------- Métodos de pago ----------

def test_solo_se_acepta_efectivo(escenario):
    _, alumno = escenario
    pagina = alumno.get(f"/estudiante/tiendas/{ids()['tienda']}").text
    assert "Nequi" in pagina and "Tarjeta débito" in pagina and "Tarjeta crédito" in pagina
    assert pagina.count("Pronto") == 3

    for metodo in ("nequi", "debito", "credito", "bitcoin"):
        assert "solo puedes pagar en efectivo" in pedir(alumno, metodo_pago=metodo).text
    assert contar_pedidos() == 0

    pedir(alumno, metodo_pago="efectivo")
    assert uno("SELECT metodo_pago FROM pedidos")["metodo_pago"] == "efectivo"


# ---------- El estudiante cancela ----------

def test_estudiante_cancela_pedido_pendiente(escenario):
    tienda, alumno = escenario
    pedir(alumno)
    pedido_id = uno("SELECT id FROM pedidos")["id"]
    respuesta = alumno.post(f"/estudiante/pedidos/{pedido_id}/cancelar")
    assert "Cancelaste el pedido" in respuesta.text
    assert uno("SELECT estado FROM pedidos")["estado"] == "cancelado"
    assert "canceló el pedido" in tienda.get("/notificaciones").text


def test_no_se_cancela_un_pedido_aceptado_ni_ajeno(escenario, cliente, nuevo_cliente):
    tienda, alumno = escenario
    pedir(alumno)
    pedido_id = uno("SELECT id FROM pedidos")["id"]

    registrar(cliente, "3200000002", universidad=USB)
    otro = nuevo_cliente()
    entrar(otro, "3200000002")
    otro.post(f"/estudiante/pedidos/{pedido_id}/cancelar")
    assert uno("SELECT estado FROM pedidos")["estado"] == "pendiente"

    tienda.post(f"/tienda/pedidos/{pedido_id}/estado", data={"estado": "aceptado"})
    respuesta = alumno.post(f"/estudiante/pedidos/{pedido_id}/cancelar")
    assert "ya no se puede cancelar" in respuesta.text
    assert uno("SELECT estado FROM pedidos")["estado"] == "aceptado"


# ---------- Fotos de productos ----------

def test_foto_de_producto(escenario, cliente, nuevo_cliente):
    tienda, alumno = escenario
    tinto = ids()["tinto"]
    respuesta = tienda.post(f"/tienda/productos/{tinto}/foto", files={"foto": ("t.png", imagen(), "image/png")})
    assert "Foto de «Tinto» actualizada" in respuesta.text

    assert f"/productos/{tinto}/foto?v=" in alumno.get(f"/estudiante/tiendas/{ids()['tienda']}").text
    foto = alumno.get(f"/productos/{tinto}/foto")
    assert foto.headers["content-type"] == "image/jpeg"
    assert Image.open(io.BytesIO(foto.content)).size == (480, 480)

    # Otra tienda no puede cambiarla.
    registrar(cliente, "3100000002", rol="Tienda", nombre_tienda="Otra")
    otra = nuevo_cliente()
    entrar(otra, "3100000002")
    otra.post(f"/tienda/productos/{tinto}/foto/eliminar")
    assert uno("SELECT foto IS NOT NULL AS hay FROM productos WHERE id = %s", (tinto,))["hay"]

    tienda.post(f"/tienda/productos/{tinto}/foto/eliminar")
    assert alumno.get(f"/productos/{tinto}/foto").status_code == 404


# ---------- Pedir de nuevo ----------

def test_pedir_de_nuevo_llena_el_carrito(escenario):
    tienda, alumno = escenario
    i = ids()
    alumno.post(f"/estudiante/tiendas/{i['tienda']}/pedido",
                data={f"cantidad_{i['tinto']}": "2", f"cantidad_{i['empanada']}": "3"})
    pedido_id = uno("SELECT id FROM pedidos")["id"]
    tienda.post(f"/tienda/productos/{i['empanada']}/disponibilidad")  # Se agota la empanada.

    pagina = alumno.get(f"/estudiante/tiendas/{i['tienda']}", params={"repetir": pedido_id}).text
    assert f'name="cantidad_{i["tinto"]}" min="0" max="20"\n                       value="2"' in pagina
    assert "Ya no hay: Empanada" in pagina


def test_no_se_repite_el_pedido_de_otro(escenario, cliente, nuevo_cliente):
    _, alumno = escenario
    pedir(alumno)
    pedido_id = uno("SELECT id FROM pedidos")["id"]
    registrar(cliente, "3200000002", universidad=USB)
    otro = nuevo_cliente()
    entrar(otro, "3200000002")
    pagina = otro.get(f"/estudiante/tiendas/{ids()['tienda']}", params={"repetir": pedido_id}).text
    assert "Pusimos tu pedido anterior" not in pagina


# ---------- CSRF ----------

def test_formulario_sin_token_se_rechaza(escenario):
    _, alumno = escenario
    i = ids()
    respuesta = alumno.post(f"/estudiante/tiendas/{i['tienda']}/pedido",
                            data={f"cantidad_{i['tinto']}": "1"}, sin_csrf=True)
    assert respuesta.status_code == 403
    assert "La página venció" in respuesta.text

    respuesta = alumno.post(f"/estudiante/tiendas/{i['tienda']}/pedido",
                            data={f"cantidad_{i['tinto']}": "1", "csrf": "inventado"}, sin_csrf=True)
    assert respuesta.status_code == 403
    assert contar_pedidos() == 0


def test_login_sin_token_se_rechaza(cliente):
    registrar(cliente, "3001112233")
    assert cliente.post("/login", data={"telefono": "3001112233"}, sin_csrf=True).status_code == 403


def test_las_paginas_incluyen_el_token(escenario):
    tienda, _ = escenario
    pagina = tienda.get("/tienda/menu").text
    assert pagina.count('name="csrf"') == pagina.count('method="post"') > 0


# ---------- Migraciones ----------

def test_la_base_queda_en_la_ultima_migracion(cliente):
    assert uno("SELECT version_num FROM alembic_version")["version_num"] == "0005"


def test_universidad_de_otra_tienda_sigue_bloqueada(escenario, cliente, nuevo_cliente):
    registrar(cliente, "3200000003", universidad=ANDES)
    andes = nuevo_cliente()
    entrar(andes, "3200000003")
    assert pedir(andes).status_code == 403


# ---------- Íconos y caché del navegador ----------

def test_iconos_tienen_tamano_propio_y_estilos_versionados(escenario):
    """Si el navegador usa estilos viejos guardados, los íconos no deben crecer."""
    import re

    _, alumno = escenario
    pagina = alumno.get(f"/estudiante/tiendas/{ids()['tienda']}").text
    svgs = re.findall(r"<svg[^>]*>", pagina)
    assert svgs and all('width="' in s and 'height="' in s for s in svgs)
    assert re.search(r'href="/static/styles\.css\?v=\d+"', pagina)
    assert re.search(r'src="/static/avisos\.js\?v=\d+"', pagina)
