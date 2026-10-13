
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


        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verificar código | BEE</title>
            <style>
                * {{
                    box-sizing: border-box;
                }}

                body {{
                    margin: 0;
                    min-height: 100vh;
                    padding: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-family: Arial, sans-serif;
                    background: #F9FBFA;
                    color: #263238;
                }}

                .tarjeta {{
                    width: 100%;
                    max-width: 440px;
                    padding: 36px;
                    background: #FFFFFF;
                    border: 1px solid #E5ECEA;
                    border-radius: 20px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.07);
                }}

                .logo {{
                    margin: 0 0 28px;
                    font-size: 38px;
                    font-weight: bold;
                }}

                .logo span {{
                    color: #F7C948;
                }}

                .etiqueta {{
                    display: inline-block;
                    padding: 8px 12px;
                    border-radius: 20px;
                    background: #E4F3F1;
                    color: #357D7B;
                    font-size: 13px;
                }}

                h2 {{
                    margin: 20px 0 12px;
                    font-size: 27px;
                }}

                .descripcion {{
                    color: #64716F;
                    line-height: 1.6;
                }}

                .codigo-prueba {{
                    margin: 22px 0;
                    padding: 15px;
                    text-align: center;
                    background: #FFF8DF;
                    border: 1px solid #F7E6A5;
                    border-radius: 12px;
                }}

                .codigo-prueba strong {{
                    display: block;
                    margin-top: 6px;
                    font-size: 26px;
                    letter-spacing: 6px;
                }}

                label {{
                    display: block;
                    margin-bottom: 8px;
                    font-weight: bold;
                    font-size: 14px;
                }}

                input {{
                    width: 100%;
                    padding: 14px;
                    border: 1px solid #D5DEDB;
                    border-radius: 10px;
                    font-size: 22px;
                    letter-spacing: 6px;
                    text-align: center;
                    outline: none;
                }}

                input:focus {{
                    border-color: #357D7B;
                    box-shadow: 0 0 0 3px rgba(53, 125, 123, 0.12);
                }}

                button {{
                    width: 100%;
                    margin-top: 18px;
                    padding: 15px;
                    border: none;
                    border-radius: 10px;
                    background: #F7C948;
                    color: #263238;
                    font-size: 16px;
                    font-weight: bold;
                    cursor: pointer;
                }}

                button:hover {{
                    background: #E9B832;
                }}

                .volver {{
                    display: block;
                    margin-top: 24px;
                    color: #357D7B;
                    text-align: center;
                    text-decoration: none;
                    font-size: 14px;
                }}

                @media (max-width: 480px) {{
                    .tarjeta {{
                        padding: 26px 22px;
                    }}
                }}
            </style>
        </head>
        <body>
            <main class="tarjeta">
                <h1 class="logo">BEE<span>.</span></h1>

                <span class="etiqueta">Verificación de seguridad</span>

                <h2>Verifica tu número</h2>
                <p class="descripcion">
                    Ingresa el código de prueba para continuar con tu cuenta.
                </p>

                <div class="codigo-prueba">
                    Código de prueba
                    <strong>123456</strong>
                </div>

                <form action="/verificar-codigo" method="post">
                    <input type="hidden" name="telefono" value="{telefono}">

                    <label for="codigo">Código de seis dígitos</label>
                    <input
                        type="text"
                        id="codigo"
                        name="codigo"
                        inputmode="numeric"
                        pattern="[0-9]{{6}}"
                        maxlength="6"
                        autocomplete="one-time-code"
                        placeholder="000000"
                        required
                    >

                    <button type="submit">Verificar y continuar</button>
                </form>

                <a class="volver" href="/login">
                    Volver al inicio de sesión
                </a>
            </main>
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
        <style>
            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                min-height: 100vh;
                font-family: Arial, sans-serif;
                background: #F9FBFA;
                color: #263238;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 24px;
            }}

            main {{
                width: 100%;
                max-width: 600px;
                background: white;
                padding: 40px;
                border-radius: 20px;
                border: 1px solid #E5ECEA;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.07);
            }}

            .logo {{
                color: #263238;
                font-size: 38px;
                font-weight: bold;
                margin: 0 0 8px;
            }}

            .logo span {{
                color: #F7C948;
            }}

            .rol {{
                display: inline-block;
                background: #E4F3F1;
                color: #357D7B;
                padding: 8px 14px;
                border-radius: 20px;
                font-size: 14px;
                margin-bottom: 18px;
            }}

            h2 {{
                font-size: 28px;
                margin: 8px 0 18px;
            }}

            .contenido {{
                line-height: 1.7;
                color: #52615F;
            }}

            .acciones {{
                margin-top: 28px;
            }}

            .boton {{
                display: inline-block;
                background: #F7C948;
                color: #263238;
                text-decoration: none;
                font-weight: bold;
                padding: 13px 20px;
                border-radius: 10px;
            }}

            .boton:hover {{
                background: #E9B832;
            }}

            @media (max-width: 480px) {{
                main {{
                    padding: 26px 22px;
                }}

                h2 {{
                    font-size: 24px;
                }}
            }}
        </style>
    </head>
    <body>
        <main>
            <h1 class="logo">BEE<span>.</span></h1>

            <div class="rol">{rol}</div>

            <h2>¡Bienvenido, {nombre}!</h2>

            <section class="contenido">
                {contenido}
            </section>

            <div class="acciones">
                <a class="boton" href="/login">
                    Cerrar y volver al login
                </a>
            </div>
        </main>
    </body>
    </html>
    """
