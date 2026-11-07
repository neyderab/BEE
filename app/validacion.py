"""Validaciones de formularios compartidas."""

import re

from app.db import universidad_existe


def telefono_valido(telefono: str) -> bool:
    return re.fullmatch(r"\d{10}", telefono) is not None


def leer_universidad(valor: str, errores: dict) -> int | None:
    try:
        universidad_id = int(valor)
    except (TypeError, ValueError):
        universidad_id = None
    if universidad_id is None or not universidad_existe(universidad_id):
        errores["universidad_id"] = "Selecciona la universidad."
        return None
    return universidad_id


def validar_texto(valor: str, campo: str, etiqueta: str, maximo: int, errores: dict) -> None:
    if not valor:
        errores[campo] = f"Escribe {etiqueta}."
    elif len(valor) > maximo:
        errores[campo] = f"Máximo {maximo} caracteres."
