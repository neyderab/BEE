
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
def iniciar_sesion(telefono: str = Form(...)):
    conexion = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

    cursor = conexion.cursor()
    cursor.execute(
        "SELECT nombre FROM usuarios WHERE telefono = %s",
        (telefono,)
    )
    usuario = cursor.fetchone()
    cursor.close()
    conexion.close()

    if usuario:
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verificar código | BEE</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: #f7f7f2;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    padding: 20px;
                    box-sizing: border-box;
                }}
                .tarjeta {{
                    background: white;
                    padding: 35px;
                    border-radius: 22px;
                    width: 100%;
                    max-width: 380px;
                    box-sizing: border-box;
                    box-shadow: 0 10px 35px #00000010;
                }}
                h1 {{ font-size: 38px; margin-bottom: 10px; }}
                h1 span {{ color: #e1bc00; }}
                p {{ color: #666; line-height: 1.6; }}
                .codigo {{
                    background: #ffdf35;
                    padding: 15px;
                    border-radius: 12px;
                    text-align: center;
                    font-size: 25px;
                    font-weight: bold;
                    letter-spacing: 6px;
                    margin: 20px 0;
                }}
                input {{
                    width: 100%;
                    padding: 14px;
                    box-sizing: border-box;
                    border: 1px solid #ddd;
                    border-radius: 10px;
                    font-size: 18px;
                    margin: 10px 0 20px;
                    text-align: center;
                    letter-spacing: 5px;
                }}
                button {{
                    width: 100%;
                    padding: 15px;
                    border: none;
                    border-radius: 10px;
                    background: #202019;
                    color: white;
                    font-weight: bold;
                    cursor: pointer;
                }}
                a {{ color: #202019; }}
            </style>
        </head>
        <body>
            <div class="tarjeta">
                <h1>BEE<span>.</span></h1>
                <h2>Verifica tu número</h2>
                <p>Ingresa el código de prueba para continuar.</p>

                <p>Código de prueba:</p>
                <div class="codigo">123456</div>

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
                        placeholder="000000"
                        required
                    >
                    <button type="submit">Verificar y continuar</button>
                </form>

                <p><a href="/login">Volver al inicio de sesión</a></p>
            </div>
        </body>
        </html>
        """

    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Cuenta no encontrada | BEE</title>
    </head>
    <body>
        <h1>BEE</h1>
        <h2>¡Todavía no tienes una cuenta!</h2>
        <p>Este teléfono no está registrado en BEE.</p>
        <a href="/registro">Crear una cuenta</a>
        <br><br>
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
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>Código incorrecto | BEE</title>
        </head>
        <body>
            <h1>BEE</h1>
            <h2>Código incorrecto</h2>
            <p>Vuelve a intentarlo desde el inicio de sesión.</p>
            <a href="/login">Volver al login</a>
        </body>
        </html>
        """

    conexion = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

    cursor = conexion.cursor()
    cursor.execute(
        "SELECT nombre, rol FROM usuarios WHERE telefono = %s",
        (telefono,)
    )
    usuario = cursor.fetchone()
    cursor.close()
    conexion.close()

    if not usuario:
        return """
        <h1>BEE</h1>
        <p>La cuenta ya no está disponible.</p>
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
            body {{
                font-family: Arial, sans-serif;
                background: #f7f7f2;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                padding: 20px;
                box-sizing: border-box;
            }}
            .tarjeta {{
                background: white;
                width: 100%;
                max-width: 550px;
                padding: 35px;
                border-radius: 22px;
                box-sizing: border-box;
                box-shadow: 0 10px 35px #00000010;
            }}
            h1 {{ font-size: 38px; }}
            h1 span {{ color: #e1bc00; }}
            .rol {{
                display: inline-block;
                background: #ffdf35;
                padding: 8px 13px;
                border-radius: 20px;
                font-size: 13px;
                font-weight: bold;
            }}
            p {{ color: #666; line-height: 1.7; }}
            a {{ color: #202019; }}
        </style>
    </head>
    <body>
        <main class="tarjeta">
            <h1>BEE<span>.</span></h1>
            <p class="rol">{rol}</p>
            <h2>¡Bienvenido, {nombre}!</h2>
            {contenido}
            <p><a href="/login">Cerrar y volver al login</a></p>
        </main>
    </body>
    </html>
    """
