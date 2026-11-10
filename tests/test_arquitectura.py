"""Pruebas de arquitectura: hacen cumplir la separación Modelo-Vista-Controlador.

Si alguien pone SQL en un controlador, o hace que un modelo dependa de HTTP o
de las vistas, estas pruebas fallan (también en GitHub Actions).
"""

import ast
import re
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parent.parent / "app"
SQL = re.compile(r"\b(SELECT|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)\b")


def modulos(carpeta: str) -> list[Path]:
    return sorted(p for p in (APP / carpeta).glob("*.py") if p.name != "__init__.py")


def importaciones(archivo: Path) -> set[str]:
    nombres = set()
    for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
        if isinstance(nodo, ast.Import):
            nombres.update(a.name for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            nombres.add(nodo.module)
    return nombres


def textos(archivo: Path) -> list[str]:
    """Cadenas de texto del código (sin contar los docstrings)."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    docstrings = {
        id(n.body[0].value) for n in ast.walk(arbol)
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and n.body and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)
    }
    return [n.value for n in ast.walk(arbol) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings]


@pytest.mark.parametrize("archivo", modulos("controladores"), ids=lambda p: p.name)
def test_los_controladores_no_tienen_sql(archivo):
    con_sql = [t.strip()[:60] for t in textos(archivo) if SQL.search(t)]
    assert not con_sql, f"{archivo.name} tiene SQL; muévelo a app/modelos/: {con_sql}"


@pytest.mark.parametrize("archivo", modulos("controladores"), ids=lambda p: p.name)
def test_los_controladores_no_abren_la_base_de_datos(archivo):
    assert "app.modelos.base_datos" not in importaciones(archivo)


@pytest.mark.parametrize("archivo", modulos("modelos"), ids=lambda p: p.name)
def test_los_modelos_no_conocen_http_ni_las_vistas(archivo):
    prohibidos = {"fastapi", "starlette", "app.vistas", "app.controladores"}
    usados = {i for i in importaciones(archivo) if any(i == p or i.startswith(p + ".") for p in prohibidos)}
    assert not usados, f"{archivo.name} importa {usados}"


@pytest.mark.parametrize("archivo", modulos("vistas"), ids=lambda p: p.name)
def test_las_vistas_no_usan_controladores_ni_sql(archivo):
    assert not any(i.startswith("app.controladores") for i in importaciones(archivo))
    assert not [t for t in textos(archivo) if SQL.search(t)]


def test_estructura_mvc():
    for carpeta in ("modelos", "vistas", "controladores", "servicios"):
        assert (APP / carpeta / "__init__.py").exists() or carpeta == "vistas"
    assert (APP / "vistas" / "templates").is_dir() and (APP / "vistas" / "static").is_dir()
    sobrantes = [p.name for p in APP.glob("*.py") if p.name not in {"__init__.py", "config.py"}]
    assert not sobrantes, f"Archivos sueltos en app/: {sobrantes}. Ubícalos en su capa."
