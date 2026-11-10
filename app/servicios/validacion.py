"""Validación de formularios."""

import re

from app.modelos import universidades


def telefono_valido(telefono: str) -> bool:
    return re.fullmatch(r"\d{10}", telefono) is not None


class Formulario:
    """Datos de un formulario y sus errores, para mostrarlos junto a cada campo.

    Ejemplo:
        f = Formulario(nombre=" Ana ", telefono="300")
        f.texto("nombre", "tu nombre", 50)   # -> "Ana"
        f.telefono()                          # registra el error
        f.valido                              # -> False
    """

    def __init__(self, **valores):
        self.valores = {k: v.strip() if isinstance(v, str) else v for k, v in valores.items()}
        self.errores: dict[str, str] = {}

    def __getitem__(self, campo: str):
        return self.valores.get(campo)

    @property
    def valido(self) -> bool:
        return not self.errores

    def error(self, campo: str, mensaje: str) -> None:
        self.errores.setdefault(campo, mensaje)

    def texto(self, campo: str, etiqueta: str, maximo: int) -> str:
        valor = self.valores.get(campo) or ""
        if not valor:
            self.error(campo, f"Escribe {etiqueta}.")
        elif len(valor) > maximo:
            self.error(campo, f"Máximo {maximo} caracteres.")
        return valor

    def telefono(self, campo: str = "telefono") -> str:
        valor = self.valores.get(campo) or ""
        if not telefono_valido(valor):
            self.error(campo, "El teléfono debe tener 10 dígitos.")
        return valor

    def universidad(self, campo: str = "universidad_id") -> int | None:
        try:
            universidad_id = int(self.valores.get(campo))
        except (TypeError, ValueError):
            universidad_id = None
        if universidad_id is None or not universidades.existe(universidad_id):
            self.error(campo, "Selecciona la universidad.")
            return None
        return universidad_id
