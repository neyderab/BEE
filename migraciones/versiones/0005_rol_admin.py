"""Permite el rol «Admin» en bases creadas con la versión original de Bee.

La tabla `usuarios` original tenía la restricción `usuarios_rol_check`, que
solo aceptaba «Estudiante» y «Tienda». Se reemplaza por una que también acepta
«Admin». NOT VALID: no revisa las filas que ya existen (por si alguna tiene un
rol escrito de otra forma); solo se aplica a las nuevas y a las que se editen.

Revisión: 0005
Anterior: 0004
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS usuarios_rol_check;
        ALTER TABLE usuarios ADD CONSTRAINT usuarios_rol_check
            CHECK (rol IN ('Estudiante', 'Tienda', 'Admin')) NOT VALID;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS usuarios_rol_check;")
