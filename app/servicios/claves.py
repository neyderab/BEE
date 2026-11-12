"""Contraseñas de administrador: se guardan como hash scrypt, nunca en texto plano."""

import hashlib
import hmac
import secrets

LARGO_MINIMO = 8
LARGO_MAXIMO = 128
_N, _R, _P = 2**14, 8, 1  # Costo de scrypt: hace lento probar contraseñas a la fuerza.


def problema(clave: str, confirmacion: str | None = None) -> str | None:
    """Por qué la contraseña no sirve, o None si sirve."""
    if len(clave) < LARGO_MINIMO:
        return f"La contraseña debe tener al menos {LARGO_MINIMO} caracteres."
    if len(clave) > LARGO_MAXIMO:
        return f"La contraseña puede tener máximo {LARGO_MAXIMO} caracteres."
    if confirmacion is not None and clave != confirmacion:
        return "Las contraseñas no coinciden."
    return None


def _derivar(clave: str, sal: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(clave.encode(), salt=sal, n=n, r=r, p=p, maxmem=64 * 1024 * 1024, dklen=32)


def hashear(clave: str) -> str:
    sal = secrets.token_bytes(16)
    return f"scrypt${_N}${_R}${_P}${sal.hex()}${_derivar(clave, sal, _N, _R, _P).hex()}"


def verificar(clave: str, guardado: str | None) -> bool:
    if not guardado:
        return False
    try:
        _, n, r, p, sal, esperado = guardado.split("$")
        calculado = _derivar(clave, bytes.fromhex(sal), int(n), int(r), int(p))
    except ValueError:
        return False
    return hmac.compare_digest(calculado.hex(), esperado)
