# Migraciones (`migraciones/`)

Cambios de la base de datos, en orden, con [Alembic](https://alembic.sqlalchemy.org/). La app aplica las pendientes al arrancar (`app/modelos/base_datos.aplicar_migraciones`).

| Migración | Cambio |
|---|---|
| `0001_esquema_inicial` | Esquema inicial (`esquema_inicial.sql`), idempotente: conserva los datos existentes. |
| `0002_horario_pago_fotos` | Horario y apertura de tiendas, método de pago, fotos de productos. |
| `0003_codigo_y_avisos` | Código de recogida y suscripciones a avisos push. |
| `0004_clave_admin` | Contraseña (hash scrypt) de los administradores. |

Para un cambio nuevo: `alembic revision -m "descripción"`, escribe el SQL en `upgrade()` con un `COMMENT ON COLUMN` por campo, y después ejecuta `python scripts/generar_diccionario.py`. Nunca edites una migración que ya esté en `main`.
