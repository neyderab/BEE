"""Códigos de verificación enviados por SMS (Twilio Messaging).

Revisión: 0006
Anterior: 0005
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS codigos_verificacion (
            telefono VARCHAR(10) PRIMARY KEY,
            codigo_hash TEXT NOT NULL,
            expira_en TIMESTAMPTZ NOT NULL,
            intentos INTEGER NOT NULL DEFAULT 0,
            enviado_en TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        COMMENT ON TABLE codigos_verificacion IS 'Último código de inicio de sesión enviado por SMS a cada teléfono.';
        COMMENT ON COLUMN codigos_verificacion.telefono IS 'Teléfono de 10 dígitos al que se envió el código.';
        COMMENT ON COLUMN codigos_verificacion.codigo_hash IS 'HMAC del código (nunca el código en texto plano).';
        COMMENT ON COLUMN codigos_verificacion.expira_en IS 'Después de este momento el código ya no sirve.';
        COMMENT ON COLUMN codigos_verificacion.intentos IS 'Intentos fallidos; al llegar al máximo el código se anula.';
        COMMENT ON COLUMN codigos_verificacion.enviado_en IS 'Momento del envío; evita reenviar códigos seguidos.';
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS codigos_verificacion;")
