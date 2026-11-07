"""Entorno de Alembic: se conecta con los mismos datos del .env que la app."""

import os

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

load_dotenv()


def url_base_de_datos() -> URL:
    return URL.create(
        "postgresql+psycopg",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD") or None,
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT") or 5432),
        database=os.getenv("DB_NAME"),
        query={"sslmode": os.getenv("DB_SSLMODE", "require")},
    )


motor = create_engine(url_base_de_datos())
with motor.connect() as conexion:
    context.configure(connection=conexion, transactional_ddl=True)
    with context.begin_transaction():
        context.run_migrations()
motor.dispose()
