"""Código de recogida, notificaciones push y cerrar sesión desde Configuración."""

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import http_ece
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app import push
from app.db import ejecutar, uno
from tests.conftest import USB, entrar, registrar


@pytest.fixture
def escenario(cliente, nuevo_cliente):
    registrar(cliente, "3100000001", rol="Tienda", nombre_tienda="Café USB")
    tienda = nuevo_cliente()
    entrar(tienda, "3100000001")
    tienda.post("/tienda/menus", data={"nombre": "Bebidas"})
    tienda.post(f"/tienda/menus/{uno('SELECT id FROM menus')['id']}/productos", data={"nombre": "Tinto", "precio": "1500"})
    registrar(cliente, "3200000001", universidad=USB, nombre="Camilo")
    alumno = nuevo_cliente()
    entrar(alumno, "3200000001")
    return tienda, alumno


def pedido_listo(tienda, alumno) -> dict:
    ids = uno("SELECT t.id AS tienda, p.id AS producto FROM tiendas t, productos p")
    alumno.post(f"/estudiante/tiendas/{ids['tienda']}/pedido", data={f"cantidad_{ids['producto']}": "1"})
    pedido_id = uno("SELECT max(id) AS id FROM pedidos")["id"]
    for estado in ("aceptado", "preparando", "listo"):
        tienda.post(f"/tienda/pedidos/{pedido_id}/estado", data={"estado": estado})
    return uno("SELECT * FROM pedidos WHERE id = %s", (pedido_id,))


# ---------- Código de recogida ----------

def test_al_quedar_listo_el_estudiante_recibe_su_codigo(escenario):
    tienda, alumno = escenario
    pedido = pedido_listo(tienda, alumno)
    codigo = pedido["codigo_recogida"]
    assert codigo.isdigit() and len(codigo) == 4

    assert codigo in alumno.get("/estudiante/pedidos").text
    assert f"Muestra el código {codigo}" in alumno.get("/notificaciones").text
    # La tienda no ve el código: se lo tiene que decir el estudiante.
    assert codigo not in tienda.get("/tienda").text


def test_la_tienda_entrega_con_el_codigo_correcto(escenario):
    tienda, alumno = escenario
    pedido = pedido_listo(tienda, alumno)
    incorrecto = f"{(int(pedido['codigo_recogida']) + 1) % 10000:04d}"

    respuesta = tienda.post("/tienda/entregar", data={"codigo": incorrecto})
    assert "no corresponde" in respuesta.text
    assert uno("SELECT estado FROM pedidos")["estado"] == "listo"

    respuesta = tienda.post("/tienda/entregar", data={"codigo": pedido["codigo_recogida"]})
    assert f"Pedido #{pedido['id']} entregado a Camilo" in respuesta.text
    assert uno("SELECT estado FROM pedidos")["estado"] == "entregado"
    assert "entregado" in alumno.get("/notificaciones").text


def test_no_se_entrega_sin_codigo_ni_con_el_de_otra_tienda(escenario, cliente, nuevo_cliente):
    tienda, alumno = escenario
    pedido = pedido_listo(tienda, alumno)

    # El botón antiguo ya no sirve para entregar.
    tienda.post(f"/tienda/pedidos/{pedido['id']}/estado", data={"estado": "entregado"})
    assert uno("SELECT estado FROM pedidos")["estado"] == "listo"

    registrar(cliente, "3100000002", rol="Tienda", nombre_tienda="Otra", universidad=USB)
    otra = nuevo_cliente()
    entrar(otra, "3100000002")
    otra.post("/tienda/entregar", data={"codigo": pedido["codigo_recogida"]})
    assert uno("SELECT estado FROM pedidos")["estado"] == "listo"

    for basura in ("", "12", "abcd", "12345"):
        assert "no corresponde" in tienda.post("/tienda/entregar", data={"codigo": basura}).text


def test_los_codigos_listos_de_una_tienda_no_se_repiten(escenario, monkeypatch):
    tienda, alumno = escenario
    primero = pedido_listo(tienda, alumno)
    # Aunque el azar repita el número, el segundo pedido recibe otro código.
    valores = iter([int(primero["codigo_recogida"]), int(primero["codigo_recogida"]), 4321])
    monkeypatch.setattr("app.pedidos.secrets.randbelow", lambda _: next(valores))
    segundo = pedido_listo(tienda, alumno)
    assert segundo["codigo_recogida"] == "4321"


# ---------- Avisos push ----------

def test_suscribirse_y_desuscribirse(escenario):
    _, alumno = escenario
    assert len(alumno.get("/push/clave").json()["clave"]) > 80

    sub = {"endpoint": "https://fcm.googleapis.com/fcm/send/abc", "keys": {"p256dh": "clave", "auth": "secreto"}}
    token = alumno.token_csrf()
    assert alumno.post("/push/suscribir", json=sub, headers={"X-CSRF-Token": token}, sin_csrf=True).json()["ok"]
    assert uno("SELECT COUNT(*) AS n FROM suscripciones_push")["n"] == 1

    # Sin token CSRF, o con datos inválidos, se rechaza.
    assert alumno.post("/push/suscribir", json=sub, sin_csrf=True).status_code == 403
    malo = {"endpoint": "http://inseguro", "keys": {"p256dh": "a", "auth": "b"}}
    assert alumno.post("/push/suscribir", json=malo, headers={"X-CSRF-Token": token}, sin_csrf=True).status_code == 400

    alumno.post("/push/desuscribir", json={"endpoint": sub["endpoint"]}, headers={"X-CSRF-Token": token}, sin_csrf=True)
    assert uno("SELECT COUNT(*) AS n FROM suscripciones_push")["n"] == 0


class ServicioPushFalso(BaseHTTPRequestHandler):
    """Hace de servicio de notificaciones (como el de Google) y guarda lo que recibe."""

    recibidos: list = []
    respuesta = 201

    def do_POST(self):
        cuerpo = self.rfile.read(int(self.headers["Content-Length"]))
        ServicioPushFalso.recibidos.append((dict(self.headers), cuerpo))
        self.send_response(ServicioPushFalso.respuesta)
        self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture
def servicio_push():
    ServicioPushFalso.recibidos, ServicioPushFalso.respuesta = [], 201
    servidor = HTTPServer(("127.0.0.1", 0), ServicioPushFalso)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{servidor.server_port}/push"
    servidor.shutdown()


def test_el_aviso_llega_cifrado_y_completo(escenario, servicio_push):
    _, alumno = escenario
    usuario_id = uno("SELECT id FROM usuarios WHERE telefono = '3200000001'")["id"]
    # Claves del "celular" para poder descifrar el aviso, como lo haría el navegador.
    privada = ec.generate_private_key(ec.SECP256R1())
    publica = privada.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    secreto = b"0123456789abcdef"
    b64 = lambda d: base64.urlsafe_b64encode(d).rstrip(b"=").decode()  # noqa: E731
    ejecutar(
        "INSERT INTO suscripciones_push (usuario_id, endpoint, p256dh, auth) VALUES (%s, %s, %s, %s)",
        (usuario_id, servicio_push, b64(publica), b64(secreto)),
    )

    assert push.enviar(usuario_id, "🐝 ¡Tu pedido #1 está listo!", "/estudiante/pedidos") == 1
    encabezados, cuerpo = ServicioPushFalso.recibidos[0]
    encabezados = {k.lower(): v for k, v in encabezados.items()}
    assert encabezados["authorization"].startswith("vapid ")  # Firmado con nuestras claves VAPID.
    assert encabezados["content-encoding"] == "aes128gcm"      # Cifrado: solo el celular lo lee.
    datos = json.loads(http_ece.decrypt(cuerpo, private_key=privada, auth_secret=secreto, version="aes128gcm"))
    assert datos == {"titulo": "Bee", "cuerpo": "🐝 ¡Tu pedido #1 está listo!", "url": "/estudiante/pedidos"}


def test_si_el_celular_ya_no_existe_se_borra_la_suscripcion(escenario, servicio_push):
    usuario_id = uno("SELECT id FROM usuarios WHERE telefono = '3200000001'")["id"]
    privada = ec.generate_private_key(ec.SECP256R1())
    publica = privada.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    ejecutar(
        "INSERT INTO suscripciones_push (usuario_id, endpoint, p256dh, auth) VALUES (%s, %s, %s, %s)",
        (usuario_id, servicio_push, base64.urlsafe_b64encode(publica).decode().rstrip("="), "MDEyMzQ1Njc4OWFiY2RlZg"),
    )
    ServicioPushFalso.respuesta = 410  # «Este celular ya no existe».
    assert push.enviar(usuario_id, "hola") == 0
    assert uno("SELECT COUNT(*) AS n FROM suscripciones_push")["n"] == 0


def test_cambiar_el_pedido_envia_aviso_push(escenario, monkeypatch):
    tienda, alumno = escenario
    enviados = []
    monkeypatch.setattr("app.push.enviar_en_segundo_plano", lambda uid, texto, url="/app": enviados.append((texto, url)))
    pedido = pedido_listo(tienda, alumno)
    textos = [t for t, _ in enviados]
    assert any(t.startswith("Nuevo pedido") for t in textos)  # A la tienda.
    assert any(f"Muestra el código {pedido['codigo_recogida']}" in t for t in textos)  # Al estudiante.
    assert ("🐝 ¡Tu pedido #%d está listo! Muestra el código %s en Café USB." % (pedido["id"], pedido["codigo_recogida"]),
            "/estudiante/pedidos") in enviados


def test_service_worker_muestra_los_avisos(cliente):
    sw = cliente.get("/sw.js").text
    assert 'addEventListener("push"' in sw and "showNotification" in sw
    assert 'addEventListener("notificationclick"' in sw


# ---------- Cerrar sesión ----------

@pytest.mark.parametrize("telefono", ["3200000001", "3100000001"])
def test_cerrar_sesion_esta_junto_a_eliminar_cuenta(escenario, cliente, nuevo_cliente, telefono):
    c = nuevo_cliente()
    entrar(c, telefono)
    pagina = c.get("/configuracion").text
    cuenta, eliminar = pagina.index("Cerrar sesión</strong>"), pagina.index("Eliminar cuenta</h2>")
    assert 0 < eliminar - cuenta < 1500  # Una sección justo después de la otra.
    assert str(c.get("/logout").url).endswith("/login")
    assert str(c.get("/configuracion").url).endswith("/login")
