# Servicios (`app/servicios/`)

Apoyo transversal que usan varias capas y que no es ni Modelo, ni Vista, ni Controlador.

| Módulo | Qué hace | Lo usan |
|---|---|---|
| `csrf.py` | Token secreto en cada formulario; `verificar_csrf` lo exige en todo POST. | `main.py`, plantillas |
| `fotos.py` | Valida imágenes (máx. 5 MB) y las convierte en JPEG cuadrado. | Controladores `cuenta` y `tienda` |
| `push.py` | Claves VAPID y envío de notificaciones push cifradas, en segundo plano. | `modelos/notificaciones.py`, controlador `pwa` |
| `validacion.py` | Clase `Formulario`: lee campos, valida y acumula errores por campo. | Controladores |
| `formato.py` | `pesos(12500)` → `$12.500`. | Vistas y modelo de pedidos |
