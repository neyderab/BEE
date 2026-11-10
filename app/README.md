# `app/` — código de Bee organizado en MVC

| Carpeta | Capa | Qué contiene |
|---|---|---|
| [`modelos/`](modelos/) | **M**odelo | Datos y reglas de negocio. Todo el SQL vive aquí. |
| [`vistas/`](vistas/) | **V**ista | Plantillas HTML, estilos, JavaScript y la app instalable. |
| [`controladores/`](controladores/) | **C**ontrolador | Rutas HTTP: reciben la petición, usan el modelo y eligen la vista. |
| [`servicios/`](servicios/) | Apoyo | CSRF, fotos, avisos push, validación y formato. |
| `config.py` | Configuración | Variables de entorno, carpetas y constantes. |

El punto de entrada es [`main.py`](../main.py), en la raíz del proyecto. La explicación completa, con diagramas, está en [ARQUITECTURA.md](../ARQUITECTURA.md).
