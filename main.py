
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from pathlib import Path
import mysql.connector
load_dotenv()

app = FastAPI()


@app.get("/")
def inicio():


    return {"mensaje": "Bienvenido a BEE"}


@app.get("/registro", response_class=HTMLResponse)
def mostrar_registro():
    archivo = Path("templates/registro.html")
    return archivo.read_text()

@app.get("/login", response_class=HTMLResponse)
def mostrar_login():
    archivo = Path("templates/login.html")
    return archivo.read_text()

@app.post("/registrar", response_class=HTMLResponse)
def registrar_usuario(
    telefono: str = Form(...),
    nombre: str = Form(...),
    apellido: str = Form(...),
    rol: str = Form(...)
):
    
    

    conexion = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)
    

    cursor = conexion.cursor()

    sql = """
    INSERT INTO usuarios (telefono, nombre, apellido, rol)
    VALUES (%s, %s, %s, %s)
    """

    datos = (
        telefono,
        nombre,
        apellido,
        rol
    )

    cursor.execute(sql, datos)

    conexion.commit()

    cursor.close()
    conexion.close()

    archivo = Path("templates/registro_exitoso.html")
    return archivo.read_text()


@app.post("/login", response_class=HTMLResponse)
def iniciar_sesion(
    telefono: str = Form(...)
):

    conexion = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)

    cursor = conexion.cursor()

    sql = """
    SELECT nombre, rol
    FROM usuarios
    WHERE telefono = %s
    """

    cursor.execute(sql, (telefono,))

    usuario = cursor.fetchone()

    cursor.close()
    conexion.close()

    if usuario:

        nombre = usuario[0]
        rol = usuario[1]

        return f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>BEE</title>
        </head>

        <body>

            <h1>BEE</h1>

            <h2>¡Bienvenido, {nombre}!</h2>

            <p>Has iniciado sesión correctamente.</p>

            <p>Tu rol es: {rol}</p>

        </body>
        </html>
        """

    else:

        return """
        <html>
        <head>
            <meta charset="UTF-8">
            <title>BEE</title>
        </head>

        <body>

            <h1>BEE</h1>

            <h2>¡Todavía no tienes una cuenta!</h2>

            <p>El número de teléfono que ingresaste no está registrado en BEE.</p>

            <p>Por favor, regístrate para poder continuar.</p>

            <a href="/registro">Crear una cuenta</a>

            <br><br>

            <a href="/login">Intentar de nuevo</a>

        </body>
        </html>
        """

