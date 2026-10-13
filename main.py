
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

load_dotenv()

app = FastAPI()


def conectar_db():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dbname=os.getenv("DB_NAME"),
        sslmode="require"
    )


@app.get("/")
def inicio():
    return {"mensaje": "Bienvenido a BEE"}


@app.get("/registro", response_class=HTMLResponse)
def mostrar_registro():
    return Path("templates/registro.html").read_text()


@app.get("/login", response_class=HTMLResponse)
def mostrar_login():
    return Path("templates/login.html").read_text()


@app.post("/registrar", response_class=HTMLResponse)
def registrar_usuario(
    telefono: str = Form(...),
    nombre: str = Form(""),
    apellido: str = Form(""),
    rol: str = Form(...)
):
    with conectar_db() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO usuarios (telefono, nombre, apellido, rol)
                VALUES (%s, %s, %s, %s)
                """,
                (telefono, nombre, apellido, rol)
            )

    return Path("templates/registro_exitoso.html").read_text()


@app.post("/login", response_class=HTMLResponse)
def iniciar_sesion(telefono: str = Form(...)):
    with conectar_db() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT nombre FROM usuarios WHERE telefono = %s",
                (telefono,)
            )
            usuario = cursor.fetchone()

    if usuario:
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verificar código | BEE</title>
        </head>
        <body>
            <h1>BEE</h1>
            <h2>Verifica tu número</h2>
            <p>Ingresa el código de prueba para continuar.</p>
            <p>Código de prueba: <strong>123456</strong></p>
            <form action="/verificar-codigo" method="post">
                <input type="hidden" name="telefono" value="{telefono}">
                <label for="codigo">Código de seis dígitos</label>
                <input type="text" id="codigo" name="codigo"
                       inputmode="numeric" pattern="[0-9]{{6}}"
                       maxlength="6" required>
                <button type="submit">Verificar y continuar</button>
            </form>
            <p><a href="/login">Volver al inicio de sesión</a></p>
        </body>
        </html>
        """

    return """
    <!DOCTYPE html>
    <html lang="es">
    <head><meta charset="UTF-8"><title>Cuenta no encontrada | BEE</title></head>
    <body>
        <h1>BEE</h1>
        <h2>¡Todavía no tienes una cuenta!</h2>
        <p>Este teléfono no está registrado en BEE.</p>
        <a href="/registro">Crear una cuenta</a><br><br>
        <a href="/login">Intentar de nuevo</a>
    </body>
    </html>
    """


@app.post("/verificar-codigo", response_class=HTMLResponse)
def verificar_codigo(
    telefono: str = Form(...),
    codigo: str = Form(...)
):
    if codigo != "123456":
        return """
        <h1>BEE</h1>
        <h2>Código incorrecto</h2>
        <p>Vuelve a intentarlo.</p>
        <a href="/login">Volver al login</a>
        """

    with conectar_db() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT nombre, rol FROM usuarios WHERE telefono = %s",
                (telefono,)
            )
            usuario = cursor.fetchone()

    if not usuario:
        return """
        <h1>BEE</h1>
        <p>La cuenta no está disponible.</p>
        <a href="/login">Volver al login</a>
        """

    nombre = usuario[0] or "Usuario"
    rol = usuario[1]

    if rol == "Estudiante":
        contenido = """
        <h2>Tu experiencia BEE comienza aquí</h2>
        <p>Desde aquí podrás explorar tiendas de tu universidad.</p>
        <p>Próximamente podrás consultar productos y hacer pedidos.</p>
        """
    else:
        contenido = """
        <h2>Panel de tu tienda</h2>
        <p>Desde aquí podrás gestionar los productos y pedidos de tu tienda.</p>
        <p>Estas funciones se conectarán en las siguientes etapas del proyecto.</p>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bienvenido a BEE</title>
    </head>
    <body>
        <main>
            <h1>BEE.</h1>
            <p>{rol}</p>
            <h2>¡Bienvenido, {nombre}!</h2>
            {contenido}
            <p><a href="/login">Cerrar y volver al login</a></p>
        </main>
    </body>
    </html>
    """
