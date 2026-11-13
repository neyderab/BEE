# Servicios (`app/servicios/`)

Apoyo transversal que usan varias capas y que no es ni Modelo, ni Vista, ni Controlador.

| Módulo | Qué hace | Lo usan |
|---|---|---|
| `csrf.py` | Token secreto en cada formulario; `verificar_csrf` lo exige en todo POST. | `main.py`, plantillas |
| `fotos.py` | Valida imágenes (máx. 5 MB) y las convierte en JPEG cuadrado. | Controladores `cuenta` y `tienda` |
| `push.py` | Claves VAPID y envío de notificaciones push cifradas, en segundo plano. | `modelos/notificaciones.py`, controlador `pwa` |
| `validacion.py` | Clase `Formulario`: lee campos, valida y acumula errores por campo. | Controladores |
| `claves.py` | Contraseñas de administrador: hash scrypt con sal y verificación en tiempo constante. | Controladores `auth`, `admin`, `cuenta`; `scripts/crear_admin.py` |
| `sms.py` | Código de verificación por SMS con Twilio (crea el código, guarda su HMAC y lo envía); sin credenciales, modo de prueba (123456). | Controlador `auth` |
| `formato.py` | `pesos(12500)` → `$12.500`. | Vistas y modelo de pedidos |
