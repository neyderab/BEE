"""Esquema inicial: todo lo que existía antes de usar Alembic.

Aplica migraciones/esquema_inicial.sql, que es idempotente: en una base nueva
crea todo y en una base que ya tenía las tablas solo completa lo que falte.
No se edita: los cambios nuevos van en migraciones siguientes.
"""

import logging
from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parent.parent / "esquema_inicial.sql"


def upgrade() -> None:
    conexion = op.get_bind()
    conexion.exec_driver_sql(SQL.read_text(encoding="utf-8"))
    # Si la tabla original tiene teléfonos repetidos, el índice único no se
    # puede crear; la aplicación sigue funcionando y se avisa en el registro.
    repetidos = conexion.exec_driver_sql(
        "SELECT 1 FROM usuarios GROUP BY telefono HAVING COUNT(*) > 1 LIMIT 1"
    ).first()
    if repetidos:
        logging.getLogger(__name__).warning(
            "Hay teléfonos repetidos en la tabla usuarios; no se creó el índice único."
        )
    else:
        conexion.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS usuarios_telefono_idx ON usuarios (telefono)"
        )


def downgrade() -> None:
    raise NotImplementedError("El esquema inicial no se revierte.")
