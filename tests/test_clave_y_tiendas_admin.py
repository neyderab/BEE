"""Contraseña de los administradores y sección «Tiendas» del panel."""

import pytest

from app.modelos import permisos as P
from app.modelos import usuarios
from app.modelos.base_datos import uno
from app.servicios import claves
from scripts.crear_admin import main as crear_admin
from tests.conftest import CLAVE_ADMIN, USB, entrar, registrar


def crear_admin_con(telefono, permisos=P.TODOS, clave=CLAVE_ADMIN):
    return usuarios.crear(telefono, "Admin", "Prueba", "Admin", None, permisos=permisos,
                          clave_hash=claves.hashear(clave) if clave else None)


def pasar_codigo(c, telefono):
    c.post("/login", data={"telefono": telefono})
    return c.post("/verificar-codigo", data={"codigo": "123456"})


# ---------- Contraseña ----------

def test_las_claves_se_guardan_como_hash():
    guardado = claves.hashear("mi-clave-larga")
    assert "mi-clave-larga" not in guardado and guardado.startswith("scrypt$")
    assert claves.verificar("mi-clave-larga", guardado)
    assert not claves.verificar("otra-clave", guardado)
    assert not claves.verificar("lo-que-sea", None)
    assert claves.problema("corta") and claves.problema("larga-123", "distinta") and not claves.problema("larga-123")


def test_el_admin_necesita_codigo_y_contrasena(cliente):
    crear_admin_con("3000000001")
    respuesta = pasar_codigo(cliente, "3000000001")
    assert 'action="/verificar-clave"' in respuesta.text
    # Con solo el código no entra al panel.
    assert str(cliente.get("/admin").url).endswith("/login")

    pasar_codigo(cliente, "3000000001")
    respuesta = cliente.post("/verificar-clave", data={"clave": CLAVE_ADMIN})
    assert str(respuesta.url).endswith("/admin")


def test_contrasena_incorrecta_y_limite_de_intentos(cliente):
    crear_admin_con("3000000001")
    pasar_codigo(cliente, "3000000001")
    respuesta = cliente.post("/verificar-clave", data={"clave": "equivocada"})
    assert respuesta.status_code == 400 and "Te quedan 4 intentos" in respuesta.text
    for _ in range(4):
        respuesta = cliente.post("/verificar-clave", data={"clave": "equivocada"})
    assert "Demasiados intentos" in respuesta.text
    # Ya no puede seguir probando sin volver a empezar.
    respuesta = cliente.post("/verificar-clave", data={"clave": CLAVE_ADMIN})
    assert str(respuesta.url).endswith("/login")
    assert str(cliente.get("/admin").url).endswith("/login")


def test_admin_sin_contrasena_no_entra(cliente):
    crear_admin_con("3000000001", clave=None)
    respuesta = pasar_codigo(cliente, "3000000001")
    assert respuesta.status_code == 403 and "todavía no tiene contraseña" in respuesta.text
    assert str(cliente.get("/admin").url).endswith("/login")


def test_estudiantes_y_tiendas_no_piden_contrasena(cliente):
    registrar(cliente, "3200000001")
    assert str(entrar(cliente, "3200000001", clave=None).url).endswith("/estudiante")


def test_script_pone_contrasena_a_un_admin_existente(cliente):
    crear_admin_con("3000000001", clave=None)
    assert crear_admin(["3000000001", "Neyder", "Arenas"], clave="nueva-clave-9") == 0
    assert str(entrar(cliente, "3000000001", clave="nueva-clave-9").url).endswith("/admin")


def test_script_rechaza_contrasena_corta(cliente):
    assert crear_admin(["3000000001", "Neyder", "Arenas"], clave="corta") == 1
    assert usuarios.buscar_por_telefono("3000000001") is None


def test_admin_cambia_su_contrasena(cliente):
    crear_admin_con("3000000001")
    entrar(cliente, "3000000001")
    respuesta = cliente.post("/configuracion/clave", data={"actual": "mala", "nueva": "otra-clave-1", "confirmacion": "otra-clave-1"})
    assert "contraseña actual no es correcta" in respuesta.text
    respuesta = cliente.post("/configuracion/clave", data={"actual": CLAVE_ADMIN, "nueva": "otra-clave-1", "confirmacion": "otra-clave-1"})
    assert "Tu contraseña se cambió" in respuesta.text
    cliente.get("/logout")
    assert str(entrar(cliente, "3000000001", clave="otra-clave-1").url).endswith("/admin")


def test_crear_admin_desde_el_panel_exige_contrasena(cliente, nuevo_cliente):
    crear_admin_con("3000000001")
    entrar(cliente, "3000000001")
    datos = {"rol": "Admin", "telefono": "3000000002", "nombre": "Otro", "apellido": "Admin",
             "permisos": [P.VER_USUARIOS], "clave": "corta"}
    respuesta = cliente.post("/admin/usuarios", data=datos)
    assert respuesta.status_code == 400 and "al menos 8 caracteres" in respuesta.text
    cliente.post("/admin/usuarios", data={**datos, "clave": "clave-inicial-1"})
    otro = nuevo_cliente()
    assert str(entrar(otro, "3000000002", clave="clave-inicial-1").url).endswith("/admin")


def test_restablecer_contrasena_de_otro_admin(cliente, nuevo_cliente):
    crear_admin_con("3000000001")
    objetivo = crear_admin_con("3000000002", [P.VER_USUARIOS])
    entrar(cliente, "3000000001")
    respuesta = cliente.post(f"/admin/usuarios/{objetivo}/clave", data={"clave": "restablecida-1"})
    assert "Contraseña restablecida" in respuesta.text
    otro = nuevo_cliente()
    assert str(entrar(otro, "3000000002", clave="restablecida-1").url).endswith("/admin")
    # Sin «Gestionar administradores» no se puede.
    otro.post(f"/admin/usuarios/{uno('SELECT id FROM usuarios WHERE telefono = %s', ('3000000001',))['id']}/clave",
              data={"clave": "intento-malo-1"})
    assert claves.verificar(CLAVE_ADMIN, usuarios.leer_clave_hash(uno("SELECT id FROM usuarios WHERE telefono = '3000000001'")["id"]))


# ---------- Sección Tiendas ----------

@pytest.fixture
def con_tienda(cliente, nuevo_cliente):
    registrar(cliente, "3100000001", rol="Tienda", nombre_tienda="Café USB")
    dueno = nuevo_cliente()
    entrar(dueno, "3100000001")
    dueno.post("/tienda/menus", data={"nombre": "Bebidas"})
    menu_id = uno("SELECT id FROM menus")["id"]
    dueno.post(f"/tienda/menus/{menu_id}/productos", data={"nombre": "Tinto", "precio": "1500"})
    crear_admin_con("3000000001")
    admin = nuevo_cliente()
    entrar(admin, "3000000001")
    return admin, uno("SELECT id FROM tiendas")["id"]


def test_admin_ve_la_lista_y_el_detalle_de_tiendas(con_tienda):
    admin, tienda_id = con_tienda
    lista = admin.get("/admin/tiendas")
    assert lista.status_code == 200 and "Café USB" in lista.text and USB in lista.text
    assert "Café USB" not in admin.get("/admin/tiendas", params={"q": "nada-que-ver"}).text
    detalle = admin.get(f"/admin/tiendas/{tienda_id}")
    assert "Tinto" in detalle.text and "Eliminar tienda" in detalle.text
    assert admin.get("/admin/tiendas/99999").status_code == 404


def test_suspender_tienda_la_oculta_a_los_estudiantes(con_tienda, nuevo_cliente, cliente):
    admin, tienda_id = con_tienda
    registrar(cliente, "3200000001")
    alumno = nuevo_cliente()
    entrar(alumno, "3200000001", clave=None)
    assert "Café USB" in alumno.get("/estudiante").text

    respuesta = admin.post(f"/admin/tiendas/{tienda_id}/estado", data={"activo": "0"})
    assert "quedó suspendida" in respuesta.text
    assert "Café USB" not in alumno.get("/estudiante").text
    assert alumno.get(f"/estudiante/tiendas/{tienda_id}").status_code == 404

    admin.post(f"/admin/tiendas/{tienda_id}/estado", data={"activo": "1"})
    assert "Café USB" in alumno.get("/estudiante").text


def test_eliminar_tienda(con_tienda):
    admin, tienda_id = con_tienda
    respuesta = admin.post(f"/admin/tiendas/{tienda_id}/eliminar")
    assert "Se eliminó la tienda «Café USB»" in respuesta.text
    assert uno("SELECT COUNT(*) AS n FROM tiendas")["n"] == 0
    assert usuarios.buscar_por_telefono("3100000001") is None


def test_no_se_elimina_una_tienda_con_pedidos_en_curso(con_tienda, cliente, nuevo_cliente):
    admin, tienda_id = con_tienda
    registrar(cliente, "3200000001")
    alumno = nuevo_cliente()
    entrar(alumno, "3200000001", clave=None)
    producto = uno("SELECT id FROM productos")["id"]
    alumno.post(f"/estudiante/tiendas/{tienda_id}/pedido", data={f"cantidad_{producto}": "1"})
    respuesta = admin.post(f"/admin/tiendas/{tienda_id}/eliminar")
    assert "pedido(s) en curso" in respuesta.text
    assert uno("SELECT COUNT(*) AS n FROM tiendas")["n"] == 1


def test_permisos_de_la_seccion_tiendas(con_tienda, nuevo_cliente):
    _, tienda_id = con_tienda
    crear_admin_con("3000000002", [P.VER_PEDIDOS])
    sin_ver = nuevo_cliente()
    entrar(sin_ver, "3000000002")
    assert sin_ver.get("/admin/tiendas").status_code == 403

    crear_admin_con("3000000003", [P.VER_USUARIOS])
    solo_ver = nuevo_cliente()
    entrar(solo_ver, "3000000003")
    assert "Eliminar tienda" not in solo_ver.get(f"/admin/tiendas/{tienda_id}").text
    assert solo_ver.post(f"/admin/tiendas/{tienda_id}/eliminar").status_code == 403
    assert uno("SELECT COUNT(*) AS n FROM tiendas")["n"] == 1


# ---------- Editar el teléfono ----------

def test_admin_cambia_el_telefono_de_un_usuario(cliente, nuevo_cliente):
    crear_admin_con("3000000001")
    objetivo = crear_admin_con("3000000002", [P.VER_USUARIOS])
    registrar(cliente, "3200000001")
    entrar(cliente, "3000000001")
    datos = {"nombre": "Nuevo", "apellido": "Nombre"}
    respuesta = cliente.post(f"/admin/usuarios/{objetivo}/datos", data={**datos, "telefono": "3200000001"})
    assert "ya es de otra cuenta" in respuesta.text
    respuesta = cliente.post(f"/admin/usuarios/{objetivo}/datos", data={**datos, "telefono": "12"})
    assert "10 dígitos" in respuesta.text
    respuesta = cliente.post(f"/admin/usuarios/{objetivo}/datos", data={**datos, "telefono": "3000000099"})
    assert "Datos actualizados" in respuesta.text
    assert usuarios.buscar_por_telefono("3000000002") is None
    otro = nuevo_cliente()
    assert str(entrar(otro, "3000000099").url).endswith("/admin")


def test_admin_cambia_su_propio_telefono(cliente):
    yo = crear_admin_con("3000000001")
    entrar(cliente, "3000000001")
    cliente.post(f"/admin/usuarios/{yo}/datos", data={"nombre": "Neyder", "apellido": "Arenas", "telefono": "3000000077"})
    cliente.get("/logout")
    assert str(entrar(cliente, "3000000077").url).endswith("/admin")


# ---------- Bases que vienen de la versión original ----------

def test_migracion_permite_admin_en_bases_con_la_restriccion_vieja(cliente):
    """La tabla original solo aceptaba Estudiante y Tienda; la migración 0005 lo corrige."""
    from app.modelos.base_datos import aplicar_migraciones, conectar

    with conectar() as conexion:
        conexion.execute("ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS usuarios_rol_check")
        conexion.execute("ALTER TABLE usuarios ADD CONSTRAINT usuarios_rol_check CHECK (rol IN ('Estudiante', 'Tienda'))")
        conexion.execute("UPDATE alembic_version SET version_num = '0004'")
    aplicar_migraciones()
    assert crear_admin(["3000000001", "Neyder", "Arenas"], clave=CLAVE_ADMIN) == 0
    assert str(entrar(cliente, "3000000001").url).endswith("/admin")
