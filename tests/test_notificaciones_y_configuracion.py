import io

import pytest
from PIL import Image

from app.db import conectar
from tests.conftest import USB, entrar, registrar


@pytest.fixture
def escenario(cliente, nuevo_cliente):
    """Tienda en San Buenaventura con un producto y un estudiante de la misma universidad."""
    registrar(cliente, "3100000001", rol="Tienda", nombre_tienda="Café USB")
    tienda = nuevo_cliente()
    entrar(tienda, "3100000001")
    tienda.post("/tienda/menus", data={"nombre": "Bebidas"})
    with conectar() as conexion:
        menu_id = conexion.execute("SELECT id FROM menus").fetchone()["id"]
    tienda.post(f"/tienda/menus/{menu_id}/productos", data={"nombre": "Tinto", "precio": "1500"})

    registrar(cliente, "3200000001", universidad=USB)
    alumno = nuevo_cliente()
    entrar(alumno, "3200000001")

    with conectar() as conexion:
        ids = conexion.execute(
            "SELECT t.id AS tienda_id, p.id AS producto_id FROM tiendas t, productos p"
        ).fetchone()
    return tienda, alumno, ids


def pedir(alumno, ids, cantidad=1):
    return alumno.post(
        f"/estudiante/tiendas/{ids['tienda_id']}/pedido",
        data={f"cantidad_{ids['producto_id']}": str(cantidad)},
    )


def ultimo_pedido():
    with conectar() as conexion:
        return conexion.execute("SELECT * FROM pedidos ORDER BY id DESC LIMIT 1").fetchone()


def notificaciones_de(telefono):
    with conectar() as conexion:
        return [
            f["texto"]
            for f in conexion.execute(
                """
                SELECT n.texto FROM notificaciones n JOIN usuarios u ON u.id = n.usuario_id
                WHERE u.telefono = %s ORDER BY n.id
                """,
                (telefono,),
            )
        ]


# ---------- Tiempo de preparación y aceptación ----------

def test_tienda_configura_tiempo_y_el_pedido_lo_guarda(escenario):
    tienda, alumno, ids = escenario
    respuesta = tienda.post("/tienda/disponibilidad", data={"tiempo_min": "20"})
    assert "20–25 min" in respuesta.text

    assert "20–25 min" in alumno.get(f"/estudiante/tiendas/{ids['tienda_id']}").text
    pedir(alumno, ids)
    pedido = ultimo_pedido()
    assert (pedido["tiempo_min"], pedido["tiempo_max"]) == (20, 25)


@pytest.mark.parametrize("valor", ["7", "30", "0", "abc", ""])
def test_tiempo_invalido_no_se_guarda(escenario, valor):
    tienda, _, _ = escenario
    respuesta = tienda.post("/tienda/disponibilidad", data={"tiempo_min": valor})
    assert "tiempo de preparación válido" in respuesta.text
    with conectar() as conexion:
        assert conexion.execute("SELECT tiempo_min FROM tiendas").fetchone()["tiempo_min"] == 10


def test_sin_auto_aceptar_la_tienda_acepta_manualmente(escenario):
    tienda, alumno, ids = escenario
    pedir(alumno, ids)
    pedido = ultimo_pedido()
    assert pedido["estado"] == "pendiente" and pedido["aceptado_en"] is None
    assert any("Nuevo pedido" in t and "Acéptalo" in t for t in notificaciones_de("3100000001"))

    tienda.post(f"/tienda/pedidos/{pedido['id']}/estado", data={"estado": "aceptado"})
    pedido = ultimo_pedido()
    assert pedido["estado"] == "aceptado" and pedido["aceptado_en"] is not None
    assert notificaciones_de("3200000001") == [
        f"Café USB aceptó tu pedido #{pedido['id']}. Estará listo en 10–15 min."
    ]
    assert "Pásalo a recoger entre" in alumno.get("/estudiante/pedidos").text


def test_con_auto_aceptar_el_pedido_entra_aceptado(escenario):
    tienda, alumno, ids = escenario
    tienda.post("/tienda/disponibilidad", data={"tiempo_min": "5", "auto_aceptar": "on"})
    respuesta = pedir(alumno, ids)
    assert "aceptó tu pedido" in respuesta.text

    pedido = ultimo_pedido()
    assert pedido["estado"] == "aceptado" and pedido["aceptado_en"] is not None
    assert any("aceptado automáticamente" in t for t in notificaciones_de("3100000001"))
    assert any("aceptó tu pedido" in t and "5–10 min" in t for t in notificaciones_de("3200000001"))


def test_estudiante_recibe_una_notificacion_por_cada_cambio(escenario):
    tienda, alumno, ids = escenario
    pedir(alumno, ids)
    pedido_id = ultimo_pedido()["id"]
    for estado in ("aceptado", "preparando", "listo", "entregado"):
        tienda.post(f"/tienda/pedidos/{pedido_id}/estado", data={"estado": estado})
    textos = notificaciones_de("3200000001")
    assert len(textos) == 4
    assert "en preparación" in textos[1]
    assert "está listo" in textos[2]
    assert "entregado" in textos[3]


def test_cancelacion_avisa_al_estudiante(escenario):
    tienda, alumno, ids = escenario
    pedir(alumno, ids)
    pedido_id = ultimo_pedido()["id"]
    tienda.post(f"/tienda/pedidos/{pedido_id}/estado", data={"estado": "cancelado"})
    assert notificaciones_de("3200000001") == [f"Café USB canceló tu pedido #{pedido_id}."]
    assert "La tienda canceló este pedido" in alumno.get("/estudiante/pedidos").text


# ---------- Campana de notificaciones ----------

def test_resumen_y_marcar_como_leidas(escenario):
    tienda, alumno, ids = escenario
    pedir(alumno, ids)
    resumen = tienda.get("/notificaciones/resumen").json()
    assert resumen["sin_leer"] == 1
    assert "Nuevo pedido" in resumen["ultima_texto"]

    pagina = tienda.get("/notificaciones").text
    assert "Nuevo pedido" in pagina
    assert tienda.get("/notificaciones/resumen").json()["sin_leer"] == 0

    # Cada usuario ve solo sus notificaciones.
    assert alumno.get("/notificaciones/resumen").json()["sin_leer"] == 0


# ---------- Configuración ----------

def imagen(formato="PNG", tamano=(800, 600)):
    salida = io.BytesIO()
    Image.new("RGB", tamano, (255, 200, 0)).save(salida, formato)
    return salida.getvalue()


def test_cambiar_nombre_y_nombre_de_tienda(escenario):
    tienda, alumno, _ = escenario
    respuesta = alumno.post("/configuracion/perfil", data={"nombre": "Ana María", "apellido": "Ruiz"})
    assert "Tus datos se guardaron" in respuesta.text
    assert 'value="Ana María"' in respuesta.text

    tienda.post(
        "/configuracion/perfil",
        data={"nombre": "Laura", "apellido": "Gómez", "nombre_tienda": "Café Bloque C"},
    )
    with conectar() as conexion:
        assert conexion.execute("SELECT nombre FROM tiendas").fetchone()["nombre"] == "Café Bloque C"


def test_perfil_valida_datos(escenario):
    _, alumno, _ = escenario
    respuesta = alumno.post("/configuracion/perfil", data={"nombre": "", "apellido": "x" * 60})
    assert respuesta.status_code == 400
    assert "Escribe tu nombre" in respuesta.text and "Máximo 50" in respuesta.text


def test_subir_y_quitar_foto(escenario):
    tienda, alumno, _ = escenario
    respuesta = alumno.post("/configuracion/foto", files={"foto": ("yo.png", imagen(), "image/png")})
    assert "se actualizó" in respuesta.text

    with conectar() as conexion:
        alumno_id = conexion.execute(
            "SELECT id FROM usuarios WHERE telefono = '3200000001'"
        ).fetchone()["id"]
    foto = alumno.get(f"/fotos/{alumno_id}")
    assert foto.headers["content-type"] == "image/jpeg"
    assert Image.open(io.BytesIO(foto.content)).size == (256, 256)

    alumno.post("/configuracion/foto/eliminar")
    assert alumno.get(f"/fotos/{alumno_id}").status_code == 404


def test_archivo_que_no_es_imagen_se_rechaza(escenario):
    _, alumno, _ = escenario
    respuesta = alumno.post(
        "/configuracion/foto", files={"foto": ("virus.png", b"no soy una imagen", "image/png")}
    )
    assert "no es una imagen válida" in respuesta.text


def test_foto_demasiado_pesada_se_rechaza(escenario):
    _, alumno, _ = escenario
    pesada = b"0" * (5 * 1024 * 1024 + 10)
    respuesta = alumno.post("/configuracion/foto", files={"foto": ("grande.png", pesada, "image/png")})
    assert "más de 5 MB" in respuesta.text


def test_fotos_requieren_sesion(cliente):
    assert str(cliente.get("/fotos/1").url).endswith("/login")


# ---------- Cerrar cuenta ----------

def test_estudiante_cierra_su_cuenta(escenario):
    tienda, alumno, ids = escenario
    pedir(alumno, ids)
    pedido_id = ultimo_pedido()["id"]

    # Con un pedido en curso no se puede cerrar.
    respuesta = alumno.post("/configuracion/cerrar-cuenta", data={"confirmacion": "ELIMINAR"})
    assert "pedidos en curso" in respuesta.text

    tienda.post(f"/tienda/pedidos/{pedido_id}/estado", data={"estado": "cancelado"})

    # Sin la palabra de confirmación tampoco.
    respuesta = alumno.post("/configuracion/cerrar-cuenta", data={"confirmacion": "si"})
    assert "Escribe ELIMINAR" in respuesta.text

    respuesta = alumno.post("/configuracion/cerrar-cuenta", data={"confirmacion": "eliminar"})
    assert "Tu cuenta se cerró" in respuesta.text
    with conectar() as conexion:
        assert conexion.execute(
            "SELECT 1 FROM usuarios WHERE telefono = '3200000001'"
        ).fetchone() is None
        # El pedido sigue en el historial de la tienda, sin datos del estudiante.
        assert conexion.execute("SELECT estudiante_id FROM pedidos").fetchone()["estudiante_id"] is None

    assert "Cuenta eliminada" in tienda.get("/tienda").text
    assert str(alumno.get("/estudiante").url).endswith("/login")


def test_tienda_no_puede_cerrar_cuenta_desde_la_app(escenario):
    tienda, _, _ = escenario
    pagina = tienda.get("/configuracion").text
    assert "mailto:admin@usebeeapp.com" in pagina

    respuesta = tienda.post("/configuracion/cerrar-cuenta", data={"confirmacion": "ELIMINAR"})
    assert "escríbenos por correo" in respuesta.text
    with conectar() as conexion:
        assert conexion.execute("SELECT COUNT(*) AS n FROM tiendas").fetchone()["n"] == 1
