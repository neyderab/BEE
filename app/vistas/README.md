# Vista (`app/vistas/`)

La **V** de MVC: lo que ve el usuario. Se genera en el servidor con Jinja2, que **escapa el HTML automáticamente** (protección contra XSS).

```text
vistas/
├── plantillas.py       Configura Jinja2 y ofrece render() y mostrar_mensaje()
├── templates/
│   ├── layouts/        base.html · auth_base.html (login y registro) · app_base.html (con sesión)
│   ├── parciales/      Piezas reutilizables: avatar, íconos, mensajes, campos, avisos
│   ├── auth/           Login, registro, verificación, completar perfil
│   ├── estudiante/     Tiendas, menú con carrito y pago, mis pedidos
│   ├── tienda/         Tablero de pedidos, menú y precios
│   ├── admin/          Panel, usuarios, pedidos, universidades
│   ├── cuenta/         Configuración, avisos, cuenta eliminada
│   ├── pwa/            Instalar la app, sin conexión
│   └── errores/        Error y página vencida
└── static/
    ├── styles.css      Estilos de toda la app (el estudiante tiene diseño de app con barra inferior)
    ├── avisos.js       Campana: revisa novedades cada 15 s
    ├── push.js         Botón «Activar avisos» (notificaciones push)
    └── pwa/            manifest, service worker (sw.js) e íconos de la app instalable
```

## Reglas

- Una plantilla **no consulta la base de datos**: muestra lo que le pasa el controlador. Las únicas excepciones son las constantes del negocio (por ejemplo `ESTADOS`) y el contador de avisos, que `plantillas.py` expone como funciones globales.
- Todo `<form method="post">` lleva `{{ campo_csrf() }}`.
- Los archivos de `static/` se enlazan con `{{ estatico('archivo') }}`, que agrega la versión (`?v=...`) para que el navegador no use una copia vieja.
