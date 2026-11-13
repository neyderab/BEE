"""Códigos de verificación por SMS: se guarda solo su HMAC, con vencimiento e intentos."""

from app.modelos.base_datos import conectar, ejecutar, uno

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
            "SELECT codigo_hash, intentos FROM codigos_verificacion WHERE telefono = %s AND expira_en > now() FOR UPDATE",
            (telefono,),
        ).fetchone()
        if fila is None or fila["intentos"] >= MAXIMO_INTENTOS:
            return False
        if coincide(fila["codigo_hash"]):
            conexion.execute("DELETE FROM codigos_verificacion WHERE telefono = %s", (telefono,))
            return True
        conexion.execute("UPDATE codigos_verificacion SET intentos = intentos + 1 WHERE telefono = %s", (telefono,))
        return False


def borrar(telefono: str) -> None:
    ejecutar("DELETE FROM codigos_verificacion WHERE telefono = %s", (telefono,))
