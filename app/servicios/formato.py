"""Formatos para mostrar datos (los usan las vistas y los mensajes)."""


def pesos(valor: int) -> str:
    """12500 -> '$12.500'"""
    return "$" + f"{int(valor):,}".replace(",", ".")
