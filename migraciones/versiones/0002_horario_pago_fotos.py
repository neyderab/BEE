"""Horario de las tiendas, método de pago y fotos de productos.

Revisión: 0002
Anterior: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE tiendas ADD COLUMN abierta BOOLEAN NOT NULL DEFAULT TRUE;
        ALTER TABLE tiendas ADD COLUMN hora_apertura TIME;
        ALTER TABLE tiendas ADD COLUMN hora_cierre TIME;
        ALTER TABLE tiendas ADD CONSTRAINT tiendas_horario_completo
            CHECK ((hora_apertura IS NULL) = (hora_cierre IS NULL));

        ALTER TABLE pedidos ADD COLUMN metodo_pago VARCHAR(20) NOT NULL DEFAULT 'efectivo';

        ALTER TABLE productos ADD COLUMN foto BYTEA;
        ALTER TABLE productos ADD COLUMN foto_actualizada TIMESTAMPTZ;

        COMMENT ON COLUMN tiendas.abierta IS 'Interruptor de la tienda: si es falso no recibe pedidos.';
        COMMENT ON COLUMN tiendas.hora_apertura IS 'Hora en que abre cada día (vacío: sin horario fijo).';
        COMMENT ON COLUMN tiendas.hora_cierre IS 'Hora en que cierra cada día (vacío: sin horario fijo).';
        COMMENT ON COLUMN pedidos.metodo_pago IS 'efectivo (por ahora el único disponible); nequi y tarjetas llegarán después.';
        COMMENT ON COLUMN productos.foto IS 'Foto del producto en JPEG de 480×480.';
        COMMENT ON COLUMN productos.foto_actualizada IS 'Momento del último cambio de foto.';
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE productos DROP COLUMN foto_actualizada, DROP COLUMN foto;
        ALTER TABLE pedidos DROP COLUMN metodo_pago;
        ALTER TABLE tiendas DROP CONSTRAINT tiendas_horario_completo,
            DROP COLUMN hora_cierre, DROP COLUMN hora_apertura, DROP COLUMN abierta;
    """)
