"""Paquete principal de Bee (capas MVC). Ver ARQUITECTURA.md."""

import sys

if sys.version_info < (3, 10):
    raise SystemExit(
        f"Bee necesita Python 3.10 o superior y estás usando Python {sys.version.split()[0]}.\n"
        "Instala Python 3.12 (python.org o «brew install python@3.12») y vuelve a crear el entorno:\n"
        "  rm -rf .venv && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    )
