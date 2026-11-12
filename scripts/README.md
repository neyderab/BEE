# Herramientas (`scripts/`)

Se ejecutan a mano desde la raíz del proyecto, con la base de datos configurada en `.env`.

| Script | Para qué |
|---|---|
| `python scripts/crear_admin.py 3001234567 Nombre Apellido` | Crea el primer administrador (todos los permisos) y le pide una contraseña. Con un admin existente, cambia su contraseña. |
| `python scripts/generar_claves_push.py` | Crea las claves VAPID de las notificaciones push (para Render). |
| `python scripts/generar_diccionario.py` | Regenera `docs/diccionario.html` desde la base real. |
