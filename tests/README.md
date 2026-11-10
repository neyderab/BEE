# Pruebas (`tests/`)

Se ejecutan con `pytest` contra una base PostgreSQL **solo para pruebas** (las pruebas borran y recrean las tablas). En GitHub corren solas en cada pull request (`.github/workflows/pruebas.yml`).

```bash
TEST_DB_HOST=localhost TEST_DB_USER=postgres TEST_DB_PASSWORD=tu_clave TEST_DB_NAME=bee_test TEST_DB_SSLMODE=disable pytest
```

| Archivo | Qué prueba |
|---|---|
| `test_arquitectura.py` | La separación MVC: sin SQL en controladores, modelos sin HTTP, vistas sin SQL. |
| `test_registro.py` | Registro, inicio de sesión, verificación y seguridad del login. |
| `test_tiendas_y_pedidos.py` | Menús, productos, pedidos y la regla de la misma universidad. |
| `test_notificaciones_y_configuracion.py` | Tiempos, aceptación, avisos, configuración, fotos y eliminar cuenta. |
| `test_admin.py` | Administradores y permisos. |
| `test_experiencia.py` | Horario de tiendas, pagos, cancelar, fotos de productos, pedir de nuevo, CSRF y migraciones. |
| `test_codigo_y_avisos.py` | Código de recogida y notificaciones push (cifrado de extremo a extremo). |
| `test_app_instalable.py` | App instalable (manifest, service worker) y página web en celular. |

`conftest.py` prepara la base y ofrece `ClienteBee`, un cliente de pruebas que agrega el token CSRF a cada POST como lo haría el navegador.
