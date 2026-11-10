"""Configuración de Bee: rutas del proyecto, variables de entorno y constantes.

Todo lo que depende del entorno (base de datos, claves) se lee de variables
de entorno; en desarrollo vienen del archivo .env (ver .env.example).
"""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

# ---------- Carpetas ----------
VISTAS = RAIZ / "app" / "vistas"
PLANTILLAS = VISTAS / "templates"
ESTATICOS = VISTAS / "static"
PRESENTACION = RAIZ / "docs"           # Página de presentación (también en GitHub Pages).
MIGRACIONES = RAIZ / "alembic.ini"

# ---------- Seguridad ----------
SECRET_KEY = os.getenv("SECRET_KEY") or "solo-para-desarrollo-cambiar"
SECRET_KEY_DE_DESARROLLO = not os.getenv("SECRET_KEY")
COOKIE_SEGURA = os.getenv("COOKIE_SEGURA") == "1"  # En producción (HTTPS): 1.

# ---------- Negocio ----------
ZONA_HORARIA = ZoneInfo("America/Bogota")
CORREO_SOPORTE = "admin@usebeeapp.com"
CODIGO_PRUEBA = "123456"  # Código de verificación fijo mientras no exista el envío por SMS.
