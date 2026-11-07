# Bee — Buy, Enjoy & Exit

[![Pruebas](https://github.com/neyderab/BEE/actions/workflows/pruebas.yml/badge.svg)](https://github.com/neyderab/BEE/actions/workflows/pruebas.yml)

**Pide antes. Recoge sin fila.**

Bee es un proyecto de desarrollo de software que busca mejorar la experiencia de compra dentro de las universidades mediante una plataforma que permite a los estudiantes consultar productos, realizar pedidos anticipadamente y recogerlos en un horario seleccionado, reduciendo los tiempos de espera en las tiendas universitarias.

##  Descripción del proyecto

Durante los descansos universitarios, los estudiantes suelen encontrar filas y tiempos de espera en las tiendas y cafeterías del campus. Bee propone una alternativa digital para organizar las compras de manera rápida, sencilla y eficiente.

La plataforma busca conectar a los estudiantes con las tiendas disponibles dentro de su universidad, facilitando la consulta de productos y la gestión de pedidos.

##  Objetivos

- Reducir los tiempos de espera en las tiendas universitarias.
- Facilitar la consulta de productos y sus precios.
- Permitir que los estudiantes realicen pedidos anticipadamente.
- Organizar los pedidos mediante horarios de recogida.
- Mejorar la organización de las compras dentro del campus.
- Ofrecer a las tiendas una herramienta para gestionar sus productos y pedidos.

##  Funcionalidades principales

### Para estudiantes
- Registro de usuarios.
- Inicio de sesión mediante número de teléfono.
- Verificación de acceso mediante código.
- Selección de universidad.
- Consulta de tiendas disponibles.
- Exploración de productos y precios.
- Realización y organización de pedidos.
- Selección de horario de recogida.

### Para las tiendas
- Gestión de la información de la tienda.
- Administración del catálogo de productos.
- Consulta y gestión de pedidos recibidos.

*Nota: las funcionalidades descritas representan el alcance previsto del proyecto; algunas pueden encontrarse todavía en desarrollo.*

## Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| HTML | Estructura de las páginas web |
| CSS | Diseño y estilos de la interfaz |
| Python | Desarrollo del backend |
| FastAPI | Creación de rutas y servicios web |
| PostgreSQL | Base de datos |
| Jinja2 | Plantillas HTML |
| Git y GitHub | Control de versiones y alojamiento del código |
| GitHub Pages | Publicación de la página de presentación |

## Programación Orientada a Objetos (POO)

El proyecto contempla la organización del sistema mediante entidades que representan sus componentes principales:

- **Estudiante:** representa al usuario que realiza los pedidos.
- **Universidad:** agrupa las tiendas disponibles y los estudiantes asociados.
- **Tienda:** representa el establecimiento que ofrece productos.
- **Producto:** contiene información como nombre, precio y disponibilidad.
- **Pedido:** registra los productos solicitados, su estado y el horario de recogida.

Estas entidades sirven como base conceptual para organizar la información y las responsabilidades del sistema.

## Cómo funciona hoy

- **Registro:** el usuario elige si es *estudiante* o *tienda* y selecciona su universidad. Las tiendas también escriben el nombre de la tienda.
- **Universidades disponibles:** Universidad de San Buenaventura, Universidad Nacional de Colombia, Pontificia Universidad Javeriana, Universidad de los Andes y Universidad del Rosario (se crean en la primera migración).
- **Inicio de sesión:** con el teléfono y un código de verificación (por ahora el código de prueba `123456`).
- **Panel de la tienda** (`/tienda`):
  - Abre o cierra la tienda con un botón y, si quiere, define un horario fijo (por ejemplo de 7:00 a 18:00). Cerrada, no recibe pedidos.
  - Define en cuánto tiempo se pueden recoger los pedidos: 5–10, 10–15, 15–20, 20–25 o 25–30 minutos.
  - Elige si acepta los pedidos **automáticamente** o **manualmente**.
  - Ve los pedidos en columnas (Por aceptar, Aceptado, En preparación, Listo para recoger) y los avanza con un botón.
  - En "Menú y precios" crea menús, agrega productos con precio y foto, los edita y los marca como agotados.
- **Vista del estudiante** (`/estudiante`), diseñada como una app para el celular, con barra inferior **Tiendas · Pedidos · Avisos · Perfil**:
  - Ve solo las tiendas de **su universidad**, si están abiertas y su tiempo de preparación.
  - Agrega productos con los botones − y +, revisa el carrito y elige cómo pagar. Por ahora solo **efectivo** (al recoger); Nequi, tarjeta débito y tarjeta crédito aparecen como «Pronto».
  - Sigue cada pedido con una barra de progreso, lo **cancela** mientras la tienda no lo haya aceptado y lo **pide de nuevo** con un toque.
- **Notificaciones:** la campana 🔔 avisa al estudiante cuando la tienda acepta, prepara, termina o cancela su pedido, y a la tienda cuando llega un pedido nuevo. Las páginas de pedidos se actualizan solas.
- **Configuración** (`/configuracion`): ambos usuarios cambian su foto de perfil y su nombre (la tienda también el nombre de la tienda). El estudiante puede cerrar su cuenta desde ahí; la tienda debe escribir a admin@usebeeapp.com.
- **Administración** (`/admin`): los administradores crean estudiantes, tiendas y otros administradores, editan datos, suspenden o eliminan cuentas, ven los pedidos de todas las tiendas y agregan universidades. Cada administrador solo puede hacer lo que sus **permisos** le autorizan (ver más abajo).
- **Regla de universidad:** un estudiante solo puede hacer pedidos en tiendas de su misma universidad. El servidor lo verifica en cada pedido.

## Administradores y permisos

Nadie puede registrarse como administrador desde la web. El **primer administrador** se crea desde la terminal, con la base de datos configurada en `.env`; recibe todos los permisos:

```bash
python scripts/crear_admin.py 3001234567 Nombre Apellido
```

Después, ese administrador entra con su teléfono y crea a los demás en **Usuarios → Nuevo usuario**, marcando los permisos de cada uno:

| Permiso | Qué permite |
|---|---|
| Ver usuarios | Consultar la lista de usuarios y sus datos |
| Crear usuarios | Registrar estudiantes y tiendas |
| Editar usuarios | Cambiar nombres y universidad; suspender o reactivar cuentas |
| Eliminar usuarios | Borrar cuentas (no se permite si tienen pedidos en curso) |
| Gestionar administradores | Crear otros administradores y asignarles permisos |
| Ver pedidos | Consultar los pedidos de todas las tiendas |
| Gestionar universidades | Agregar universidades nuevas |

Reglas de seguridad:
- Nadie puede dar un permiso que no tiene.
- Nadie puede cambiar sus propios permisos, suspenderse ni eliminarse.
- Para crear, editar, suspender o eliminar a otro administrador se necesita «Gestionar administradores». Así siempre queda al menos un administrador con ese permiso.

## Estructura del proyecto

```text
BEE/
├── main.py                 # Crea la app FastAPI y registra las rutas
├── alembic.ini             # Configuración de las migraciones
├── migraciones/            # Cambios de la base de datos, en orden (Alembic)
├── render.yaml             # Configuración para publicar en Render
├── app/
│   ├── db.py               # Conexión a PostgreSQL
│   ├── sesion.py           # Usuario en sesión y permisos por rol
│   ├── permisos.py         # Permisos de los administradores
│   ├── usuarios.py         # Creación de usuarios
│   ├── validacion.py       # Clase Formulario (validaciones)
│   ├── csrf.py             # Protección de formularios
│   ├── fotos.py            # Fotos de perfil y de productos
│   ├── plantillas.py       # Jinja2 y mensajes
│   ├── pedidos.py          # Estados, tiempos, horario, pagos y notificaciones
│   └── rutas/
│       ├── auth.py         # Registro, login, verificación, perfil
│       ├── tienda.py       # Panel de la tienda
│       ├── estudiante.py   # Tiendas y pedidos del estudiante
│       ├── cuenta.py       # Notificaciones, configuración y foto
│       └── admin.py        # Panel de administración
├── scripts/
│   ├── crear_admin.py      # Crea el primer administrador
│   └── generar_diccionario.py  # Regenera docs/diccionario.html desde la base
├── templates/              # Páginas HTML (Jinja2)
├── static/                 # Estilos y JavaScript de los avisos
├── tests/                  # Pruebas automáticas (pytest)
├── .github/workflows/      # Pruebas automáticas en GitHub
└── docs/                   # Página de presentación (GitHub Pages)
```

## Ejecución local del backend

Necesitas Python 3.10 o superior y una base de datos PostgreSQL.

1. Clona el repositorio y entra en la carpeta:

```bash
git clone https://github.com/neyderab/BEE.git
```

```bash
cd BEE
```

2. Crea y activa un entorno virtual (macOS o Linux):

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

3. Instala las dependencias:

```bash
pip install -r requirements.txt
```

4. Copia `.env.example` como `.env` y completa los datos de la base de datos y `SECRET_KEY`.

5. Inicia el servidor. Al arrancar, la aplicación aplica las migraciones pendientes de la base de datos (ver «Migraciones»). Los datos existentes se conservan.

```bash
python3 main.py
```

6. Abre http://127.0.0.1:8000 en el navegador.

### Pruebas

Las pruebas **borran y recrean todas las tablas**, así que usa una base de datos separada solo para pruebas:

```bash
TEST_DB_HOST=localhost TEST_DB_USER=postgres TEST_DB_PASSWORD=tu_clave TEST_DB_NAME=bee_test TEST_DB_SSLMODE=disable pytest
```

En GitHub las pruebas se ejecutan solas en cada pull request (`.github/workflows/pruebas.yml`). Si alguna falla, el pull request muestra una ❌ y no conviene unirlo hasta arreglarla.

### Migraciones

La estructura de la base de datos se maneja con [Alembic](https://alembic.sqlalchemy.org/) en `migraciones/versiones/`: cada cambio es un archivo numerado (`0001_…`, `0002_…`). La aplicación aplica las pendientes al arrancar. Para cambiar la base:

1. Crea una migración: `alembic revision -m "describe el cambio"`.
2. Escribe el SQL en `upgrade()` (y cómo deshacerlo en `downgrade()`). Agrega un `COMMENT ON COLUMN` para cada campo nuevo.
3. Actualiza el diccionario de datos: `python scripts/generar_diccionario.py`.

No se editan migraciones que ya estén en `main`; los cambios siempre van en una migración nueva.

### Seguridad de los formularios

Todos los formularios llevan un token CSRF (`app/csrf.py`): otra página web no puede enviarlos en nombre del usuario. En las plantillas se agrega con `{{ campo_csrf() }}` dentro de cada `<form method="post">`.

## Publicar la aplicación

La aplicación también sirve la página de presentación (`docs/`) en la raíz. Si **usebeeapp.com** apunta a la aplicación publicada, la portada sigue igual y los botones **Iniciar sesión** y **Registrarse** funcionan. Mientras el dominio apunte a GitHub Pages, esos botones no tienen a dónde llevar.

Pasos en [Render](https://render.com):

1. **New → Blueprint** y elige este repositorio (usa `render.yaml`).
2. Completa `DB_HOST`, `DB_USER`, `DB_PASSWORD` y `DB_NAME` con la base PostgreSQL que ya usan. `SECRET_KEY` se genera sola.
3. Cuando esté funcionando, crea el primer administrador desde la pestaña **Shell** del servicio: `python scripts/crear_admin.py 3001234567 Nombre Apellido`.
4. En **Settings → Custom Domains** agrega `usebeeapp.com` y cambia los registros DNS del dominio como indique Render. Después desactiva GitHub Pages en el repositorio.

> ⚠️ Antes de publicar para usuarios reales hay que reemplazar el código de prueba `123456` por el envío real de SMS. Con el código fijo, cualquiera que conozca un teléfono puede entrar a esa cuenta, incluidas las de administrador.

## Diccionario de datos

`docs/diccionario.html` se genera desde la base de datos real, con las descripciones (`COMMENT`) de las migraciones. Después de agregar una migración, actualízalo con:

```bash
python scripts/generar_diccionario.py
```

## Página del proyecto

- **Repositorio:** https://github.com/neyderab/BEE
- **Sitio web:** https://usebeeapp.com

## Equipo de desarrollo

Proyecto desarrollado por:

| Integrante | Rol |
|---|---|
| **Neyder Arenas** | Programación y backend |
| **Nicole Lamprea** | Diseño visual y CSS |
| **Camilo Cueto** | Documentación y pruebas |
| **Daniel Muñoz** | Documentación, implementación de proyectos y pruebas |

## Documentación

El repositorio puede incluir documentos relacionados con los objetivos, requisitos, diseño, diccionario de datos y presentación académica del proyecto.

Consulta las carpetas y archivos del repositorio para acceder a los documentos disponibles.

## Proyección del proyecto

Bee busca evolucionar hacia una plataforma que facilite la interacción entre estudiantes y tiendas universitarias, con posibilidades de ampliar sus funcionalidades, mejorar la experiencia de usuario y facilitar la gestión de pedidos.

## 📄 Estado del proyecto

**En desarrollo.**

Bee continúa en construcción como proyecto académico de desarrollo de software.

---

*Bee — Buy, Enjoy & Exit. Pide antes. Recoge sin fila.*
