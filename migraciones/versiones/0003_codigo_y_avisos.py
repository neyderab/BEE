"""Código de recogida de los pedidos y suscripciones a notificaciones push.

Revisión: 0003
Anterior: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE pedidos ADD COLUMN codigo_recogida VARCHAR(4);
        -- Los pedidos que ya estaban listos reciben su código.
        UPDATE pedidos SET codigo_recogida = lpad(floor(random() * 10000)::int::text, 4, '0')
        WHERE estado = 'listo' AND codigo_recogida IS NULL;

        CREATE TABLE suscripciones_push (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES usuarios (id) ON DELETE CASCADE,
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            creada_en TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX suscripciones_push_usuario_idx ON suscripciones_push (usuario_id);

        COMMENT ON COLUMN pedidos.codigo_recogida IS 'Código de 4 dígitos que el estudiante muestra para recoger; se crea cuando el pedido está listo.';
        COMMENT ON TABLE suscripciones_push IS 'Celulares y navegadores que reciben notificaciones push de un usuario.';
        COMMENT ON COLUMN suscripciones_push.id IS 'Identificador de la suscripción.';
        COMMENT ON COLUMN suscripciones_push.usuario_id IS 'Usuario que recibe los avisos.';
        COMMENT ON COLUMN suscripciones_push.endpoint IS 'Dirección del servicio de notificaciones del navegador.';
        COMMENT ON COLUMN suscripciones_push.p256dh IS 'Clave pública del navegador para cifrar el aviso.';
        COMMENT ON COLUMN suscripciones_push.auth IS 'Secreto del navegador para cifrar el aviso.';
        COMMENT ON COLUMN suscripciones_push.creada_en IS 'Momento en que se activaron los avisos.';
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE suscripciones_push;
        ALTER TABLE pedidos DROP COLUMN codigo_recogida;
    """)
