from app.db import conectar
from tests.conftest import ANDES, USB, entrar, id_universidad, registrar


def test_hay_cinco_universidades_incluida_san_buenaventura(cliente):
    respuesta = cliente.get("/registro")
    assert respuesta.status_code == 200
    with conectar() as conexion:
        nombres = [f["nombre"] for f in conexion.execute("SELECT nombre FROM universidades")]
    assert len(nombres) == 5
    assert USB in nombres
    for nombre in nombres:
        assert nombre in respuesta.text


def test_registro_estudiante_guarda_universidad(cliente):
    respuesta = registrar(cliente, "3001112233")
    assert respuesta.status_code == 200
    assert "Ya eres parte de BEE" in respuesta.text
    with conectar() as conexion:
        usuario = conexion.execute(
            "SELECT rol, universidad_id FROM usuarios WHERE telefono = '3001112233'"
        ).fetchone()
    assert usuario == {"rol": "Estudiante", "universidad_id": id_universidad(USB)}


def test_registro_exige_universidad(cliente):
    respuesta = cliente.post(
        "/registrar",
        data={"telefono": "3001112233", "nombre": "Ana", "apellido": "P", "rol": "Estudiante"},
    )
    assert respuesta.status_code == 400
    assert "Selecciona tu universidad" in respuesta.text


def test_registro_valida_datos_en_el_servidor(cliente):
    respuesta = registrar(cliente, "123", rol="Administrador", nombre="")
    assert respuesta.status_code == 400
    assert "10 dígitos" in respuesta.text
    assert "Elige si eres estudiante o tienda" in respuesta.text
    assert "Escribe tu nombre" in respuesta.text


def test_registro_tienda_exige_nombre_de_tienda(cliente):
    respuesta = registrar(cliente, "3001112233", rol="Tienda")
    assert respuesta.status_code == 400
    assert "nombre de la tienda" in respuesta.text

    respuesta = registrar(cliente, "3001112233", rol="Tienda", universidad=ANDES, nombre_tienda="Café Andes")
    assert respuesta.status_code == 200
    with conectar() as conexion:
        assert conexion.execute("SELECT nombre FROM tiendas").fetchone()["nombre"] == "Café Andes"


def test_telefono_repetido_muestra_mensaje(cliente):
    registrar(cliente, "3001112233")
    respuesta = registrar(cliente, "3001112233")
    assert respuesta.status_code == 400
    assert "ya está registrado" in respuesta.text


def test_html_se_escapa(cliente):
    registrar(cliente, "3001112233", nombre="<script>alert(1)</script>")
    respuesta = entrar(cliente, "3001112233")
    assert "<script>alert(1)</script>" not in respuesta.text
    assert "&lt;script&gt;" in respuesta.text


def test_login_redirige_segun_rol(cliente, nuevo_cliente):
    registrar(cliente, "3001112233")
    registrar(cliente, "3004445566", rol="Tienda", nombre_tienda="Café USB")

    estudiante = nuevo_cliente()
    assert str(entrar(estudiante, "3001112233").url).endswith("/estudiante")

    tienda = nuevo_cliente()
    assert str(entrar(tienda, "3004445566").url).endswith("/tienda")

    # Un estudiante no puede entrar al panel de la tienda.
    assert str(estudiante.get("/tienda").url).endswith("/estudiante")


def test_codigo_incorrecto(cliente):
    registrar(cliente, "3001112233")
    respuesta = cliente.post("/verificar-codigo", data={"telefono": "3001112233", "codigo": "000000"})
    assert respuesta.status_code == 400
    assert "no es correcto" in respuesta.text


def test_paginas_privadas_piden_sesion(cliente):
    for ruta in ("/tienda", "/tienda/menu", "/estudiante", "/estudiante/pedidos"):
        assert str(cliente.get(ruta).url).endswith("/login")


def test_usuario_antiguo_sin_universidad_completa_su_perfil(cliente):
    with conectar() as conexion:
        conexion.execute(
            "INSERT INTO usuarios (telefono, nombre, apellido, rol) "
            "VALUES ('3009998877', 'Leo', 'Ruiz', 'Tienda')"
        )
    respuesta = entrar(cliente, "3009998877")
    assert str(respuesta.url).endswith("/completar-perfil")

    respuesta = cliente.post(
        "/completar-perfil",
        data={"universidad_id": id_universidad(USB), "nombre_tienda": "Tienda Leo"},
    )
    assert str(respuesta.url).endswith("/tienda")
    assert "Tienda Leo" in respuesta.text
