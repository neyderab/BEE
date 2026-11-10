"""Tiendas: horario, disponibilidad y consultas para los estudiantes."""

from datetime import datetime, time

from app.config import ZONA_HORARIA
from app.modelos.base_datos import ejecutar, todos, uno

# Opciones de tiempo de preparación: 5 -> "5–10 min", ..., 25 -> "25–30 min".
TIEMPOS = (5, 10, 15, 20, 25)
RANGO_MINUTOS = 5


def texto_tiempo(tiempo_min: int) -> str:
    return f"{tiempo_min}–{tiempo_min + RANGO_MINUTOS} min"


# ---------- Horario (reglas de negocio) ----------

def tienda_abierta(tienda: dict, ahora: datetime | None = None) -> bool:
    """Abierta si su interruptor está encendido y, si tiene horario, está dentro de él."""
    if not tienda.get("abierta"):
        return False
    apertura, cierre = tienda.get("hora_apertura"), tienda.get("hora_cierre")
    if apertura is None or cierre is None:
        return True
    hora = (ahora or datetime.now(ZONA_HORARIA)).astimezone(ZONA_HORARIA).time()
    if apertura <= cierre:
        return apertura <= hora < cierre
    return hora >= apertura or hora < cierre  # Horario que pasa la medianoche.


def estado_tienda(tienda: dict) -> str:
    """Texto corto para el estudiante, por ejemplo «Cierra a las 18:00»."""
    apertura, cierre = tienda.get("hora_apertura"), tienda.get("hora_cierre")
    if tienda_abierta(tienda):
        return f"Cierra a las {cierre:%H:%M}" if cierre else "Recibiendo pedidos"
    if tienda.get("abierta") and apertura:
        return f"Abre a las {apertura:%H:%M}"
    return "No recibe pedidos por ahora"


def leer_hora(texto: str) -> time | None:
    try:
        return time.fromisoformat(texto.strip())
    except ValueError:
        return None


# ---------- Consultas ----------

def buscar(tienda_id: int) -> dict | None:
    """La tienda con su universidad y su dueño (propietario_id)."""
    return uno(
        """
        SELECT t.id, t.nombre, t.tiempo_min, t.auto_aceptar, t.usuario_id AS propietario_id,
               t.abierta, t.hora_apertura, t.hora_cierre,
               u.universidad_id, un.nombre AS universidad
        FROM tiendas t
        JOIN usuarios u ON u.id = t.usuario_id
        JOIN universidades un ON un.id = u.universidad_id
        WHERE t.id = %s
        """,
        (tienda_id,),
    )


def listar_de_universidad(universidad_id: int) -> list[dict]:
    """Tiendas de una universidad, primero las abiertas, con cuántos productos tienen."""
    tiendas = todos(
        """
        SELECT t.id, t.nombre, t.tiempo_min, t.abierta, t.hora_apertura, t.hora_cierre,
               COUNT(p.id) FILTER (WHERE p.disponible) AS productos
        FROM tiendas t
        JOIN usuarios u ON u.id = t.usuario_id
        LEFT JOIN menus m ON m.tienda_id = t.id
        LEFT JOIN productos p ON p.menu_id = m.id
        WHERE u.universidad_id = %s
        GROUP BY t.id
        ORDER BY t.nombre
        """,
        (universidad_id,),
    )
    return sorted(tiendas, key=lambda t: not tienda_abierta(t))


# ---------- Cambios ----------

def guardar_disponibilidad(tienda_id: int, tiempo_min: int, auto_aceptar: bool, apertura, cierre) -> None:
    ejecutar(
        "UPDATE tiendas SET tiempo_min = %s, auto_aceptar = %s, hora_apertura = %s, hora_cierre = %s WHERE id = %s",
        (tiempo_min, auto_aceptar, apertura, cierre, tienda_id),
    )


def alternar_abierta(tienda_id: int) -> bool:
    """Abre o cierra la tienda. Devuelve True si quedó abierta."""
    return uno("UPDATE tiendas SET abierta = NOT abierta WHERE id = %s RETURNING abierta", (tienda_id,))["abierta"]
