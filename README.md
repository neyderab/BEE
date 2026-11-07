# Bee — Buy, Enjoy & Exit

**Pide antes. Recoge sin fila.**

BEE es un proyecto de desarrollo de software que busca mejorar la experiencia de compra dentro de las universidades mediante una plataforma que permite a los estudiantes consultar productos, realizar pedidos anticipadamente y recogerlos en un horario seleccionado, reduciendo los tiempos de espera en las tiendas universitarias.

##  Descripción del proyecto

Durante los descansos universitarios, los estudiantes suelen encontrar filas y tiempos de espera en las tiendas y cafeterías del campus. BEE propone una alternativa digital para organizar las compras de manera rápida, sencilla y eficiente.

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
- **Universidades disponibles:** Universidad de San Buenaventura, Universidad Nacional de Colombia, Pontificia Universidad Javeriana, Universidad de los Andes y Universidad del Rosario (se crean en `schema.sql`).
- **Inicio de sesión:** con el teléfono y un código de verificación (por ahora el código de prueba `123456`).
- **Panel de la tienda** (`/tienda`): crea menús (por ejemplo "Desayunos"), agrega productos con precio, los edita, los marca como agotados y gestiona los pedidos (pendiente → en preparación → listo → entregado, o cancelado).
- **Vista del estudiante** (`/estudiante`): ve solo las tiendas de **su universidad**, elige productos y hora de recogida, y sigue el estado de sus pedidos.
- **Regla de universidad:** un estudiante solo puede hacer pedidos en tiendas de su misma universidad. El servidor lo verifica en cada pedido.

## Estructura del proyecto

```text
BEE/
├── main.py                 # Crea la app FastAPI y registra las rutas
├── schema.sql              # Tablas y universidades (se aplica al iniciar)
├── app/
│   ├── db.py               # Conexión a PostgreSQL
│   ├── sesion.py           # Usuario en sesión y permisos por rol
│   ├── plantillas.py       # Jinja2 y mensajes
│   ├── pedidos.py          # Estados de pedidos y consultas compartidas
│   └── rutas/
│       ├── auth.py         # Registro, login, verificación, perfil
│       ├── tienda.py       # Panel de la tienda
│       └── estudiante.py   # Tiendas y pedidos del estudiante
├── templates/              # Páginas HTML (Jinja2)
├── static/styles.css       # Estilos compartidos
├── tests/                  # Pruebas automáticas (pytest)
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

5. Inicia el servidor. Al arrancar, la aplicación crea las tablas que falten y agrega las universidades. Si ya tenías la tabla `usuarios`, se conservan los datos: los usuarios antiguos eligen su universidad la próxima vez que inicien sesión.

```bash
python3 -m uvicorn main:app --reload
```

6. Abre http://127.0.0.1:8000 en el navegador.

### Pruebas

Las pruebas **borran y recrean todas las tablas**, así que usa una base de datos separada solo para pruebas:

```bash
TEST_DB_HOST=localhost TEST_DB_USER=postgres TEST_DB_PASSWORD=tu_clave TEST_DB_NAME=bee_test TEST_DB_SSLMODE=disable pytest
```

## Página del proyecto

- **Repositorio:** https://github.com/neyderab/BEE
- **Sitio web:** https://usebeeapp.com

## Equipo de desarrollo

Proyecto desarrollado por:

- **Camilo Cueto**
- **Neyder Arenas**
- **Nicole Lamprea**

## Documentación

El repositorio puede incluir documentos relacionados con los objetivos, requisitos, diseño, diccionario de datos y presentación académica del proyecto.

Consulta las carpetas y archivos del repositorio para acceder a los documentos disponibles.

## Proyección del proyecto

Bee busca evolucionar hacia una plataforma que facilite la interacción entre estudiantes y tiendas universitarias, con posibilidades de ampliar sus funcionalidades, mejorar la experiencia de usuario y facilitar la gestión de pedidos.

## 📄 Estado del proyecto

**En desarrollo.**

BEE continúa en construcción como proyecto académico de desarrollo de software.

---

*BEE — Buy, Enjoy & Exit. Pide antes. Recoge sin fila.*
