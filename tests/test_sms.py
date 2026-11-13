"""Código de verificación por SMS con Twilio, simulado: no se envían mensajes reales."""

import re

import httpx
import pytest

from app.modelos.base_datos import conectar, uno
from tests.conftest import registrar


class TwilioFalso:
    """Reemplaza httpx.post y responde como la API de mensajes de Twilio."""

    def __init__(self):
        self.caido, self.mensajes, self.verificados = False, [], None

    def __call__(self, url, data=None, auth=None, timeout=None):
        if self.caido:
            raise httpx.ConnectError("sin conexión")
        self.mensajes.append((url, data, auth))
        if self.verificados is not None and data["To"] not in self.verificados:
            return httpx.Response(400, json={"code": 21608, "message": "The number is unverified.", "status": 400})
        return httpx.Response(201, json={"sid": "SMprueba", "status": "queued"})

    def ultimo_codigo(self):
        return re.search(r"\b(\d{6})\b", self.mensajes[-1][1]["Body"]).group(1)


@pytest.fixture
def twilio(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACprueba")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token-de-prueba")
    monkeypatch.setenv("TWILIO_NUMERO", "+15550001111")
    falso = TwilioFalso()
    monkeypatch.setattr(httpx, "post", falso)
    return falso


def pedir_codigo(cliente, telefono="3200000001"):
    return cliente.post("/login", data={"telefono": telefono})


def test_sin_twilio_se_usa_el_codigo_de_prueba(cliente):
    registrar(cliente, "3200000001")
    pagina = pedir_codigo(cliente)
    assert "Código de prueba" in pagina.text and "123456" in pagina.text


def test_con_twilio_envia_el_sms_y_guarda_solo_el_hmac(cliente, twilio):
    registrar(cliente, "3200000001")
    pagina = pedir_codigo(cliente)
    assert "Código de prueba" not in pagina.text
    url, datos, auth = twilio.mensajes[0]
    assert url == "https://api.twilio.com/2010-04-01/Accounts/ACprueba/Messages.json"
    assert datos["To"] == "+573200000001" and datos["From"] == "+15550001111"
    assert auth == ("ACprueba", "token-de-prueba")
    guardado = uno("SELECT codigo_hash FROM codigos_verificacion")["codigo_hash"]
    assert twilio.ultimo_codigo() not in guardado


def test_con_twilio_solo_entra_con_el_codigo_que_llego_y_sirve_una_vez(cliente, twilio, nuevo_cliente):
    registrar(cliente, "3200000001")
    pedir_codigo(cliente)
    codigo = twilio.ultimo_codigo()
    malo = cliente.post("/verificar-codigo", data={"codigo": "123456" if codigo != "123456" else "654321"})
    assert malo.status_code == 400 and "no es correcto" in malo.text
    assert str(cliente.post("/verificar-codigo", data={"codigo": codigo}).url).endswith("/estudiante")
    otro = nuevo_cliente()  # El mismo código no sirve dos veces.
    otro.post("/login", data={"telefono": "3200000001"})  # Bloqueado por los 30 s: no envía otro.
    assert otro.post("/verificar-codigo", data={"codigo": codigo}).status_code == 400


def test_cinco_intentos_fallidos_anulan_el_codigo(cliente, twilio):
    registrar(cliente, "3200000001")
    pedir_codigo(cliente)
    codigo = twilio.ultimo_codigo()
    malo = "000000" if codigo != "000000" else "111111"
    for _ in range(5):
        cliente.post("/verificar-codigo", data={"codigo": malo})
    assert cliente.post("/verificar-codigo", data={"codigo": codigo}).status_code == 400


def test_el_codigo_vence(cliente, twilio):
    registrar(cliente, "3200000001")
    pedir_codigo(cliente)
    with conectar() as conexion:
        conexion.execute("UPDATE codigos_verificacion SET expira_en = now() - interval '1 minute'")
    assert cliente.post("/verificar-codigo", data={"codigo": twilio.ultimo_codigo()}).status_code == 400


def test_no_reenvia_codigos_seguidos(cliente, twilio):
    registrar(cliente, "3200000001")
    pedir_codigo(cliente)
    segunda = pedir_codigo(cliente)
    assert "Espera unos segundos" in segunda.text and len(twilio.mensajes) == 1


def test_si_twilio_falla_se_avisa_y_no_se_entra(cliente, twilio):
    registrar(cliente, "3200000001")
    twilio.caido = True
    pagina = pedir_codigo(cliente)
    assert pagina.status_code == 503 and "No pudimos enviar el SMS" in pagina.text
    assert uno("SELECT COUNT(*) AS n FROM codigos_verificacion")["n"] == 0
    assert str(cliente.get("/estudiante").url).endswith("/login")


def test_cuenta_de_prueba_envia_la_plantilla_2fa_y_acepta_su_codigo(cliente, twilio, monkeypatch):
    monkeypatch.setenv("TWILIO_CUENTA_DE_PRUEBA", "1")
    registrar(cliente, "3200000001")
    pedir_codigo(cliente)
    assert twilio.mensajes[0][1]["Body"] == "sms_2fa"
    assert cliente.post("/verificar-codigo", data={"codigo": "123456"}).status_code == 400
    assert str(cliente.post("/verificar-codigo", data={"codigo": "482913"}).url).endswith("/estudiante")


def test_cuenta_de_prueba_con_numero_no_verificado_muestra_el_codigo(cliente, twilio, monkeypatch, nuevo_cliente):
    monkeypatch.setenv("TWILIO_CUENTA_DE_PRUEBA", "1")
    twilio.verificados = {"+573200000001"}
    registrar(cliente, "3200000001")
    registrar(cliente, "3200000002")
    verificado = nuevo_cliente()
    assert "Código de prueba" not in verificado.post("/login", data={"telefono": "3200000001"}).text
    otro = nuevo_cliente()
    pagina = otro.post("/login", data={"telefono": "3200000002"})
    assert pagina.status_code == 200 and "Código de prueba" in pagina.text and "482913" in pagina.text
    assert str(otro.post("/verificar-codigo", data={"codigo": "482913"}).url).endswith("/estudiante")


def test_cuenta_paga_no_muestra_codigo_si_twilio_rechaza(cliente, twilio):
    twilio.verificados = set()  # Twilio rechaza a todos, pero sin cuenta de prueba no hay plan B.
    registrar(cliente, "3200000001")
    pagina = pedir_codigo(cliente)
    assert pagina.status_code == 503 and "482913" not in pagina.text
