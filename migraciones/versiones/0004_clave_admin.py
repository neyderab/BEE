"""Contraseña para los administradores.

Revisión: 0004
Anterior: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE usuarios ADD COLUMN clave_hash TEXT;
        COMMENT ON COLUMN usuarios.clave_hash IS 'Contraseña del administrador, guardada como hash scrypt (nunca en texto plano). Vacía para estudiantes y tiendas.';
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE usuarios DROP COLUMN clave_hash;")
