"""Códigos de verificación por SMS: se guarda solo su HMAC, con vencimiento e intentos."""

import logging

from app.modelos.base_datos import conectar, ejecutar, uno

logger = logging.getLogger(__name__)

MINUTOS_VIGENCIA = 10
MAXIMO_INTENTOS = 5
SEGUNDOS_ENTRE_ENVIOS = 30


def enviado_hace_poco(telefono: str) -> bool:
    """¿Ya se le envió un código en los últimos SEGUNDOS_ENTRE_ENVIOS? (evita gastar SMS)."""
    return uno(
        "SELECT 1 FROM codigos_verificacion WHERE telefono = %s AND enviado_en > now() - make_interval(secs => %s)",
        (telefono, SEGUNDOS_ENTRE_ENVIOS),
    ) is not None


def guardar(telefono: str, codigo_hash: str) -> None:
    """Reemplaza el código anterior del teléfono (y borra los vencidos de todos)."""
    with conectar() as conexion:
        conexion.execute("DELETE FROM codigos_verificacion WHERE expira_en < now()")
        conexion.execute(
            """
            INSERT INTO codigos_verificacion (telefono, codigo_hash, expira_en)
            VALUES (%s, %s, now() + make_interval(mins => %s))
            ON CONFLICT (telefono) DO UPDATE
            SET codigo_hash = EXCLUDED.codigo_hash, expira_en = EXCLUDED.expira_en, intentos = 0, enviado_en = now()
            """,
            (telefono, codigo_hash, MINUTOS_VIGENCIA),
        )


def comprobar(telefono: str, coincide) -> bool:
    """Usa `coincide(codigo_hash)` para revisar el código. Si es correcto lo borra (sirve una vez).

    Si no, suma un intento; al llegar a MAXIMO_INTENTOS el código se anula.
    """
    with conectar() as conexion:
        fila = conexion.execute(
            "SELECT codigo_hash, intentos, expira_en > now() AS vigente FROM codigos_verificacion WHERE telefono = %s FOR UPDATE",
            (telefono,),
        ).fetchone()
        # El motivo queda en el registro (sin el código) para poder revisar fallos en Render.
        final = f"…{telefono[-4:]}"
        if fila is None:
            logger.warning("Código rechazado para %s: no hay un código pendiente (pide uno nuevo en /login).", final)
            return False
        if not fila["vigente"]:
            logger.warning("Código rechazado para %s: venció (pasaron más de %s minutos).", final, MINUTOS_VIGENCIA)
            return False
        if fila["intentos"] >= MAXIMO_INTENTOS:
            logger.warning("Código rechazado para %s: ya se usaron los %s intentos.", final, MAXIMO_INTENTOS)
            return False
        if coincide(fila["codigo_hash"]):
            conexion.execute("DELETE FROM codigos_verificacion WHERE telefono = %s", (telefono,))
            return True
        conexion.execute("UPDATE codigos_verificacion SET intentos = intentos + 1 WHERE telefono = %s", (telefono,))
        logger.warning("Código rechazado para %s: no coincide (intento %s de %s).", final, fila["intentos"] + 1, MAXIMO_INTENTOS)
        return False


def borrar(telefono: str) -> None:
    ejecutar("DELETE FROM codigos_verificacion WHERE telefono = %s", (telefono,))
