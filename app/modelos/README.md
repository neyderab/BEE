# Modelo (`app/modelos/`)

La **M** de MVC: los datos de Bee y las reglas del negocio. **Es la única capa que escribe SQL.**

| Módulo | Responsabilidad |
|---|---|
| `base_datos.py` | Conexión a PostgreSQL, atajos `uno()`, `todos()` y `ejecutar()`, y `aplicar_migraciones()`. |
| `usuarios.py` | Roles (`Estudiante`, `Tienda`, `Admin`), crear usuarios, datos, foto, suspender y eliminar. |
| `permisos.py` | Permisos de administrador: `tiene()`, `elegibles()` y `combinar()`. |
| `universidades.py` | Listar, crear y contar universidades. |
| `tiendas.py` | Horario (`tienda_abierta`, `estado_tienda`), tiempos de preparación y tiendas de una universidad. |
| `menus.py` | Menús y productos: precios, disponibilidad y fotos. |
| `pedidos.py` | Estados y `TRANSICIONES`, pagos, código de recogida; `crear`, `cambiar_estado`, `entregar_con_codigo` y `cancelar_por_estudiante`. |
| `notificaciones.py` | La campana: `notificar()` (también dispara el aviso push), contar y marcar como leídas. |
| `suscripciones_push.py` | Celulares que reciben avisos push. |

## Reglas

- Un modelo **no importa** FastAPI, Starlette, vistas ni controladores: recibe y devuelve datos de Python (`dict`, `list`, `int`).
- Cuando una operación no se puede hacer, el modelo lo explica con una excepción (`PedidoInvalido`, `TelefonoRepetido`) o devolviendo `None`. El controlador decide qué mostrar.
- Las operaciones que cambian varias tablas usan **una sola transacción** (`with conectar() as conexion:`).
- Lo que hace una tienda solo afecta a **su** tienda: todas las consultas filtran por `tienda_id`.

`tests/test_arquitectura.py` verifica estas reglas automáticamente.
