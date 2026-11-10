"""App instalable (PWA) y página web en celular."""

import io
from pathlib import Path

from PIL import Image

from tests.conftest import entrar, registrar

DOCS = Path(__file__).resolve().parent.parent / "docs"


def test_manifest_empieza_en_la_app(cliente):
    respuesta = cliente.get("/manifest.webmanifest")
    assert respuesta.headers["content-type"].startswith("application/manifest+json")
    datos = respuesta.json()
    assert datos["start_url"] == "/app"
    assert datos["display"] == "standalone"
    assert datos["short_name"] == "Bee"
    tamanos = {(i["sizes"], i.get("purpose", "any")) for i in datos["icons"]}
    assert {("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")} <= tamanos
    for icono in datos["icons"]:
        imagen = Image.open(io.BytesIO(cliente.get(icono["src"]).content))
        assert f"{imagen.width}x{imagen.height}" == icono["sizes"]


def test_la_app_empieza_en_iniciar_sesion(cliente, nuevo_cliente):
    assert str(cliente.get("/app").url).endswith("/login")

    registrar(cliente, "3001112233")
    alumno = nuevo_cliente()
    entrar(alumno, "3001112233")
    assert str(alumno.get("/app").url).endswith("/estudiante")


def test_service_worker_y_pagina_sin_conexion(cliente):
    sw = cliente.get("/sw.js")
    assert sw.headers["content-type"].startswith("application/javascript")
    assert sw.headers["service-worker-allowed"] == "/"
    assert "/offline" in sw.text
    assert "Sin conexión" in cliente.get("/offline").text


def test_paginas_de_la_app_enlazan_el_manifest(cliente):
    for ruta in ("/login", "/registro", "/instalar"):
        pagina = cliente.get(ruta).text
        assert 'rel="manifest" href="/manifest.webmanifest"' in pagina, ruta
        assert 'serviceWorker.register("/sw.js")' in pagina, ruta


def test_pagina_instalar(cliente):
    pagina = cliente.get("/instalar").text
    assert "Instala Bee en tu celular" in pagina
    assert "Agregar a pantalla de inicio" in pagina      # iPhone
    assert "Instalar aplicación" in pagina               # Android


def test_dentro_de_la_app_se_ocultan_los_enlaces_a_la_web(cliente):
    pagina = cliente.get("/login").text
    assert 'class="volver-inicio solo-web"' in pagina
    assert "display-mode: standalone" in cliente.get("/static/styles.css").text


def test_pagina_web_tiene_menu_para_celular_y_boton_de_descarga():
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    assert 'class="menu-boton"' in html and 'aria-controls="menu-principal"' in html
    assert html.count('href="/instalar"') == 2       # En el menú y en la portada.
    assert 'href="/login"' in html and 'href="/registro"' in html
