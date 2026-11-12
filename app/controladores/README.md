# Controlador (`app/controladores/`)

La **C** de MVC: un router de FastAPI por área. Cada ruta:

1. Verifica quién es el usuario (`Depends(...)` de `dependencias.py`).
2. Lee y valida lo que escribió (`servicios/validacion.py`).
3. Le pide al **modelo** que lea o cambie los datos.
4. Elige la **vista** (`render("carpeta/plantilla.html", ...)`) o redirige.

| Módulo | Usuario | Rutas |
|---|---|---|
| `auth.py` | Todos | `/`, `/registro`, `/login`, `/verificar-codigo`, `/logout`, `/completar-perfil` |
| `estudiante.py` | Estudiante | `/estudiante`, `/estudiante/tiendas/{id}`, `/estudiante/pedidos` |
| `tienda.py` | Tienda | `/tienda` (pedidos, entregar, horario), `/tienda/menu` (menús y productos) |
| `cuenta.py` | Todos | `/notificaciones`, `/configuracion`, fotos y eliminar cuenta |
| `admin.py` | Administrador | `/admin` (usuarios, permisos, contraseñas, tiendas, pedidos, universidades) |
| `pwa.py` | Todos | `/app`, `/manifest.webmanifest`, `/sw.js`, `/instalar`, `/offline`, `/push/*` |
| `dependencias.py` | — | `usuario_en_sesion`, `estudiante_en_sesion`, `tienda_en_sesion`, `requiere_permiso(...)` |

## Reglas

- **Sin SQL.** Si necesitas un dato nuevo, agrega una función en `app/modelos/`.
- Toda ruta `POST` queda protegida con el token CSRF (`main.py` lo exige). En la plantilla, el formulario debe incluir `{{ campo_csrf() }}`.
- La vista de cada controlador está en `app/vistas/templates/<controlador>/`.
