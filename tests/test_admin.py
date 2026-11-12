import pytest

from app.modelos import permisos as P
from app.modelos import usuarios
from app.modelos.base_datos import conectar
from scripts.crear_admin import main as crear_admin
from app.servicios import claves
from tests.conftest import ANDES, CLAVE_ADMIN, USB, entrar, id_universidad, registrar


def crear_admin_con(telefono, permisos, nombre="Admin"):
    return usuarios.crear(telefono, nombre, "Prueba", "Admin", None, permisos=permisos,
                          clave_hash=claves.hashear(CLAVE_ADMIN))


def id_de(telefono):
    with conectar() as conexion:
        fila = conexion.execute("SELECT id FROM usuarios WHERE telefono = %s", (telefono,)).fetchone()
    return fila["id"] if fila else None


def permisos_de(telefono):
    with conectar() as conexion:
        return {
            f["permiso"]
            for f in conexion.execute(
                "SELECT permiso FROM permisos_usuario p JOIN usuarios u ON u.id = p.usuario_id "
                "WHERE u.telefono = %s",
                (telefono,),
            )
        }


@pytest.fixture
def superadmin(cliente, nuevo_cliente):
    crear_admin_con("3000000001", P.TODOS, nombre="Super")
    c = nuevo_cliente()
    entrar(c, "3000000001")
    return c


def nuevo(admin, **datos):
    base = {"rol": "Estudiante", "telefono": "3111111111", "nombre": "Ana", "apellido": "Ruiz",
            "universidad_id": str(id_universidad(USB)), "clave": CLAVE_ADMIN}
    return admin.post("/admin/usuarios", data={**base, **datos})


# ---------- Primer administrador ----------

def test_script_crea_el_primer_admin_con_todos_los_permisos(cliente):
    assert crear_admin(["3000000009", "Neyder", "Arenas"], clave=CLAVE_ADMIN) == 0
    assert permisos_de("3000000009") == set(P.TODOS)
    respuesta = entrar(cliente, "3000000009")
    assert str(respuesta.url).endswith("/admin")
    assert "Panel de administración" in respuesta.text


def test_script_no_convierte_otras_cuentas_en_admin(cliente):
    registrar(cliente, "3001112233")
    assert crear_admin(["3001112233", "X", "Y"], clave=CLAVE_ADMIN) == 1
    assert permisos_de("3001112233") == set()


def test_nadie_se_registra_como_admin(cliente):
    respuesta = registrar(cliente, "3001112233", rol="Admin")
    assert respuesta.status_code == 400
    assert id_de("3001112233") is None


def test_estudiantes_y_tiendas_no_entran_al_panel(cliente, nuevo_cliente):
    registrar(cliente, "3001112233")
    alumno = nuevo_cliente()
    entrar(alumno, "3001112233")
    for ruta in ("/admin", "/admin/usuarios", "/admin/pedidos"):
        assert str(alumno.get(ruta).url).endswith("/estudiante")
    assert id_de("3111111111") is None
    nuevo(alumno)
    assert id_de("3111111111") is None


# ---------- Crear usuarios ----------

def test_admin_crea_estudiante_tienda_y_admin(superadmin):
    respuesta = nuevo(superadmin)
    assert "Usuario Ana Ruiz creado" in respuesta.text

    nuevo(superadmin, rol="Tienda", telefono="3111111112", nombre_tienda="Kiosco", universidad_id=str(id_universidad(ANDES)))
    with conectar() as conexion:
        assert conexion.execute("SELECT nombre FROM tiendas").fetchone()["nombre"] == "Kiosco"

    nuevo(superadmin, rol="Admin", telefono="3111111113", universidad_id="",
          permisos=[P.VER_USUARIOS, P.VER_PEDIDOS])
    assert permisos_de("3111111113") == {P.VER_USUARIOS, P.VER_PEDIDOS}


def test_crear_usuario_valida_datos(superadmin):
    respuesta = nuevo(superadmin, telefono="12", universidad_id="")
    assert respuesta.status_code == 400
    assert "10 dígitos" in respuesta.text and "Selecciona la universidad" in respuesta.text

    nuevo(superadmin)
    respuesta = nuevo(superadmin)
    assert "Ya existe un usuario con este teléfono" in respuesta.text

    respuesta = nuevo(superadmin, rol="Admin", telefono="3111111119")
    assert "al menos un permiso" in respuesta.text


# ---------- Permisos ----------

def test_cada_pagina_exige_su_permiso(cliente, nuevo_cliente):
    crear_admin_con("3000000002", [P.VER_PEDIDOS])
    limitado = nuevo_cliente()
    entrar(limitado, "3000000002")
    assert limitado.get("/admin/pedidos").status_code == 200
    for ruta in ("/admin/usuarios", "/admin/usuarios/nuevo", "/admin/universidades"):
        respuesta = limitado.get(ruta)
        assert respuesta.status_code == 403, ruta
        assert "No tienes permiso" in respuesta.text
    assert nuevo(limitado).status_code == 403


def test_sin_gestionar_permisos_no_se_crean_admins(cliente, nuevo_cliente):
    crear_admin_con("3000000002", [P.VER_USUARIOS, P.CREAR_USUARIOS])
    a = nuevo_cliente()
    entrar(a, "3000000002")
    assert "Administrador</strong>" not in a.get("/admin/usuarios/nuevo").text
    respuesta = nuevo(a, rol="Admin", telefono="3111111113", permisos=[P.VER_USUARIOS])
    assert respuesta.status_code == 403
    assert id_de("3111111113") is None


def test_no_se_dan_permisos_que_uno_no_tiene(cliente, nuevo_cliente):
    crear_admin_con("3000000002", [P.CREAR_USUARIOS, P.GESTIONAR_PERMISOS])
    a = nuevo_cliente()
    entrar(a, "3000000002")
    nuevo(a, rol="Admin", telefono="3111111113", permisos=[P.GESTIONAR_PERMISOS, P.ELIMINAR_USUARIOS])
    assert permisos_de("3111111113") == {P.GESTIONAR_PERMISOS}


def test_editar_permisos_conserva_los_que_el_editor_no_controla(cliente, nuevo_cliente):
    crear_admin_con("3000000002", [P.GESTIONAR_PERMISOS, P.VER_USUARIOS])
    objetivo = crear_admin_con("3000000003", [P.VER_USUARIOS, P.VER_PEDIDOS])
    a = nuevo_cliente()
    entrar(a, "3000000002")
    # Le quita VER_USUARIOS y le da GESTIONAR_PERMISOS; VER_PEDIDOS no lo controla.
    a.post(f"/admin/usuarios/{objetivo}/permisos", data={"permisos": [P.GESTIONAR_PERMISOS]})
    assert permisos_de("3000000003") == {P.GESTIONAR_PERMISOS, P.VER_PEDIDOS}


def test_nadie_cambia_sus_propios_permisos_ni_se_suspende(superadmin):
    yo = id_de("3000000001")
    respuesta = superadmin.post(f"/admin/usuarios/{yo}/permisos", data={"permisos": [P.VER_USUARIOS]})
    assert "No puedes cambiar tus propios permisos" in respuesta.text
    superadmin.post(f"/admin/usuarios/{yo}/estado", data={"activo": "0"})
    superadmin.post(f"/admin/usuarios/{yo}/eliminar")
    assert permisos_de("3000000001") == set(P.TODOS)
    assert superadmin.get("/admin").status_code == 200


def test_sin_gestionar_permisos_no_se_toca_a_otro_admin(cliente, nuevo_cliente):
    crear_admin_con("3000000002", [P.VER_USUARIOS, P.EDITAR_USUARIOS, P.ELIMINAR_USUARIOS])
    otro = crear_admin_con("3000000003", P.TODOS)
    a = nuevo_cliente()
    entrar(a, "3000000002")
    assert a.post(f"/admin/usuarios/{otro}/estado", data={"activo": "0"}).status_code == 403
    assert a.post(f"/admin/usuarios/{otro}/eliminar").status_code == 403
    assert id_de("3000000003") is not None


# ---------- Suspender y eliminar ----------

def test_suspender_impide_iniciar_sesion_y_cierra_la_sesion(superadmin, cliente, nuevo_cliente):
    registrar(cliente, "3001112233")
    alumno = nuevo_cliente()
    entrar(alumno, "3001112233")
    superadmin.post(f"/admin/usuarios/{id_de('3001112233')}/estado", data={"activo": "0"})

    assert str(alumno.get("/estudiante").url).endswith("/login")
    respuesta = alumno.post("/login", data={"telefono": "3001112233"})
    assert respuesta.status_code == 403 and "suspendida" in respuesta.text

    superadmin.post(f"/admin/usuarios/{id_de('3001112233')}/estado", data={"activo": "1"})
    assert str(entrar(alumno, "3001112233").url).endswith("/estudiante")


def test_eliminar_tienda_con_pedidos_en_curso_se_bloquea(superadmin, cliente, nuevo_cliente):
    registrar(cliente, "3100000001", rol="Tienda", nombre_tienda="Café USB")
    tienda = nuevo_cliente()
    entrar(tienda, "3100000001")
    tienda.post("/tienda/menus", data={"nombre": "Bebidas"})
    with conectar() as conexion:
        menu_id = conexion.execute("SELECT id FROM menus").fetchone()["id"]
    tienda.post(f"/tienda/menus/{menu_id}/productos", data={"nombre": "Tinto", "precio": "1500"})
    registrar(cliente, "3200000001")
    alumno = nuevo_cliente()
    entrar(alumno, "3200000001")
    with conectar() as conexion:
        ids = conexion.execute("SELECT t.id AS t, p.id AS p FROM tiendas t, productos p").fetchone()
    alumno.post(f"/estudiante/tiendas/{ids['t']}/pedido", data={f"cantidad_{ids['p']}": "1"})

    tienda_id = id_de("3100000001")
    respuesta = superadmin.post(f"/admin/usuarios/{tienda_id}/eliminar")
    assert "pedido(s) en curso" in respuesta.text

    with conectar() as conexion:
        conexion.execute("UPDATE pedidos SET estado = 'entregado'")
    respuesta = superadmin.post(f"/admin/usuarios/{tienda_id}/eliminar")
    assert "Se eliminó la cuenta" in respuesta.text
    assert id_de("3100000001") is None


def test_editar_datos_de_un_estudiante(superadmin, cliente):
    registrar(cliente, "3001112233")
    uid = id_de("3001112233")
    superadmin.post(
        f"/admin/usuarios/{uid}/datos",
        data={"nombre": "Ana María", "apellido": "Pérez", "universidad_id": str(id_universidad(ANDES))},
    )
    with conectar() as conexion:
        fila = conexion.execute("SELECT nombre, universidad_id FROM usuarios WHERE id = %s", (uid,)).fetchone()
    assert fila == {"nombre": "Ana María", "universidad_id": id_universidad(ANDES)}


# ---------- Listados ----------

def test_buscar_usuarios(superadmin, cliente):
    registrar(cliente, "3001112233", nombre="Valentina")
    registrar(cliente, "3004445566", rol="Tienda", nombre="Pedro", nombre_tienda="Kiosco Central")
    pagina = superadmin.get("/admin/usuarios", params={"q": "kiosco"}).text
    assert "Kiosco Central" in pagina and "Valentina" not in pagina
    pagina = superadmin.get("/admin/usuarios", params={"rol": "Estudiante"}).text
    assert "Valentina" in pagina and "Kiosco Central" not in pagina


def test_agregar_universidad(superadmin, cliente):
    respuesta = superadmin.post("/admin/universidades", data={"nombre": "Universidad EAFIT", "ciudad": "Medellín"})
    assert "Universidad EAFIT" in respuesta.text
    assert "Universidad EAFIT" in cliente.get("/registro").text
    respuesta = superadmin.post("/admin/universidades", data={"nombre": "Universidad EAFIT", "ciudad": "Medellín"})
    assert "ya existe" in respuesta.text


def test_admin_no_puede_cerrar_su_cuenta_desde_configuracion(superadmin):
    respuesta = superadmin.post("/configuracion/cerrar-cuenta", data={"confirmacion": "ELIMINAR"})
    assert "Pide a otro administrador" in respuesta.text
    assert id_de("3000000001") is not None


def test_el_usuario_creado_por_el_admin_puede_iniciar_sesion(superadmin, nuevo_cliente):
    nuevo(superadmin)
    c = nuevo_cliente()
    assert str(entrar(c, "3111111111").url).endswith("/estudiante")
