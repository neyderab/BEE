"""Código de verificación por SMS (Twilio Verify), simulado: no se envían mensajes reales."""

import httpx
import pytest

from tests.conftest import registrar


class TwilioFalso:
    """Reemplaza httpx.post y responde como Twilio Verify."""

    def __init__(self, codigo="482913", caido=False):
        self.codigo, self.caido, self.llamadas = codigo, caido, []

    def __call__(self, url, data=None, auth=None, timeout=None):
        self.llamadas.append((url, data, auth))
        if self.caido:
            raise httpx.ConnectError("sin conexión")
        if url.endswith("/Verifications"):
            return httpx.Response(201, json={"status": "pending"})
        estado = "approved" if data["Code"] == self.codigo else "pending"
        return httpx.Response(200, json={"status": estado})


@pytest.fixture
def twilio(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACprueba")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token-de-prueba")
    monkeypatch.setenv("TWILIO_VERIFY_SERVICE_SID", "VAprueba")
    falso = TwilioFalso()
    monkeypatch.setattr(httpx, "post", falso)
    return falso


def test_sin_twilio_se_usa_el_codigo_de_prueba(cliente):
    registrar(cliente, "3200000001")
    pagina = cliente.post("/login", data={"telefono": "3200000001"})
    assert "Código de prueba" in pagina.text and "123456" in pagina.text


def test_con_twilio_envia_el_sms_y_oculta_el_codigo_de_prueba(cliente, twilio):
    registrar(cliente, "3200000001")
    pagina = cliente.post("/login", data={"telefono": "3200000001"})
    assert "Código de prueba" not in pagina.text
    url, datos, auth = twilio.llamadas[0]
    assert url == "https://verify.twilio.com/v2/Services/VAprueba/Verifications"
    assert datos["To"] == "+573200000001" and datos["Channel"] == "sms"
    assert auth == ("ACprueba", "token-de-prueba")


def test_con_twilio_solo_entra_con_el_codigo_que_llego(cliente, twilio):
    registrar(cliente, "3200000001")
    cliente.post("/login", data={"telefono": "3200000001"})
    malo = cliente.post("/verificar-codigo", data={"codigo": "123456"})  # El de prueba ya no sirve.
    assert malo.status_code == 400 and "no es correcto" in malo.text
    bueno = cliente.post("/verificar-codigo", data={"codigo": "482913"})
    assert str(bueno.url).endswith("/estudiante")


def test_si_twilio_falla_se_avisa_y_no_se_entra(cliente, twilio):
    registrar(cliente, "3200000001")
    twilio.caido = True
    pagina = cliente.post("/login", data={"telefono": "3200000001"})
    assert pagina.status_code == 503 and "No pudimos enviar el SMS" in pagina.text
    assert str(cliente.get("/estudiante").url).endswith("/login")
