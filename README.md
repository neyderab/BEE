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

## 🛠️ Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| HTML | Estructura de las páginas web |
| CSS | Diseño y estilos de la interfaz |
| Python | Desarrollo del backend |
| FastAPI | Creación de rutas y servicios web |
| MySQL | Base de datos utilizada en el desarrollo local |
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

## Estructura del proyecto

La estructura puede variar a medida que avance el desarrollo. La organización principal contempla:

```text
BEE/
├── docs/
│   ├── index.html
│   ├── styles.css
│   └── imagenes/
├── templates/
│   ├── login.html
│   ├── registro.html
│   └── registro_exitoso.html
├── main.py
├── requirements.txt
└── README.md
```

## 💻 Ejecución local del backend

Para ejecutar el backend en un entorno local, necesitas tener Python instalado y acceso a una instancia de MySQL configurada para el proyecto.

1. Clona el repositorio:

```bash
git clone https://github.com/neyderab/BEE.git
```

2. Entra en la carpeta del proyecto:

```bash
cd BEE
```

3. Crea un entorno virtual:

```bash
python3 -m venv .venv
```

4. Activa el entorno virtual en macOS o Linux:

```bash
source .venv/bin/activate
```

5. Instala las dependencias, si existe el archivo `requirements.txt`:

```bash
pip install -r requirements.txt
```

6. Configura las variables de conexión a la base de datos según la configuración de tu entorno.

7. Inicia el servidor FastAPI:

```bash
python3 -m uvicorn main:app --reload
```

8. Abre en el navegador:

- Aplicación local: http://127.0.0.1:8000
- Documentación interactiva de la API: http://127.0.0.1:8000/docs

**Importante:** los pasos anteriores requieren que el archivo `main.py`, las dependencias y la configuración de la base de datos estén presentes y correctamente configurados.

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
