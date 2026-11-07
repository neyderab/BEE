"""Genera docs/diccionario.html a partir de la base de datos real.

Lee las tablas, campos, llaves y descripciones (los COMMENT de schema.sql)
de la base configurada en .env y reescribe el diccionario conservando su
diseño. Ejecútalo después de cambiar schema.sql:

    python scripts/generar_diccionario.py
"""

import re
import sys
from html import escape
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(RAIZ / ".env")

from app.db import conectar, inicializar_db  # noqa: E402

DICCIONARIO = RAIZ / "docs" / "diccionario.html"

# Orden en que se presentan las tablas (de lo general a lo particular).
ORDEN = [
    "universidades", "usuarios", "permisos_usuario", "tiendas", "menus",
    "productos", "pedidos", "pedido_items", "notificaciones",
]

CAMPOS = """
SELECT cl.relname AS tabla, a.attname AS campo, a.attnum AS posicion,
       format_type(a.atttypid, a.atttypmod) AS tipo,
       NOT a.attnotnull AS nulo,
       pg_get_expr(d.adbin, d.adrelid) AS predeterminado,
       col_description(cl.oid, a.attnum) AS descripcion
FROM pg_class cl
JOIN pg_namespace n ON n.oid = cl.relnamespace AND n.nspname = 'public'
JOIN pg_attribute a ON a.attrelid = cl.oid AND a.attnum > 0 AND NOT a.attisdropped
LEFT JOIN pg_attrdef d ON d.adrelid = cl.oid AND d.adnum = a.attnum
WHERE cl.relkind = 'r'
"""

TABLAS = """
SELECT cl.relname AS tabla, obj_description(cl.oid) AS descripcion
FROM pg_class cl JOIN pg_namespace n ON n.oid = cl.relnamespace AND n.nspname = 'public'
WHERE cl.relkind = 'r'
"""

# Llaves primarias, foráneas y campos únicos (restricciones e índices únicos).
LLAVES = """
SELECT cl.relname AS tabla, a.attname AS campo, co.contype AS tipo,
       ref.relname AS referencia
FROM pg_constraint co
JOIN pg_class cl ON cl.oid = co.conrelid
JOIN pg_namespace n ON n.oid = cl.relnamespace AND n.nspname = 'public'
JOIN pg_attribute a ON a.attrelid = cl.oid AND a.attnum = ANY(co.conkey)
LEFT JOIN pg_class ref ON ref.oid = co.confrelid
WHERE co.contype IN ('p', 'f', 'u') AND array_length(co.conkey, 1) >= 1
UNION ALL
SELECT cl.relname, a.attname, 'u', NULL
FROM pg_index i
JOIN pg_class cl ON cl.oid = i.indrelid
JOIN pg_namespace n ON n.oid = cl.relnamespace AND n.nspname = 'public'
JOIN pg_attribute a ON a.attrelid = cl.oid AND a.attnum = i.indkey[0]
WHERE i.indisunique AND NOT i.indisprimary AND i.indnatts = 1
"""


def texto_predeterminado(valor: str | None) -> str:
    if valor is None:
        return "—"
    if valor.startswith("nextval("):
        return "automático"
    valor = re.sub(r"::[a-z ]+$", "", valor).strip("'")
    return {"now()": "fecha y hora actual", "true": "verdadero", "false": "falso"}.get(valor, valor)


def texto_llaves(tipos: set, referencias: list) -> str:
    partes = []
    if "p" in tipos:
        partes.append('<span class="key">PK</span>')
    for ref in referencias:
        partes.append(f'<span class="key">FK → {escape(ref)}</span>')
    if "u" in tipos and "p" not in tipos:
        partes.append('<span class="key">Único</span>')
    return " ".join(partes) or "—"


def main() -> None:
    inicializar_db()
    with conectar() as conexion:
        campos = conexion.execute(CAMPOS).fetchall()
        tablas = {f["tabla"]: f["descripcion"] or "" for f in conexion.execute(TABLAS)}
        llaves: dict[tuple, dict] = {}
        for f in conexion.execute(LLAVES):
            info = llaves.setdefault((f["tabla"], f["campo"]), {"tipos": set(), "refs": []})
            info["tipos"].add(f["tipo"])
            if f["tipo"] == "f" and f["referencia"] not in info["refs"]:
                info["refs"].append(f["referencia"])

    orden = [t for t in ORDEN if t in tablas] + sorted(t for t in tablas if t not in ORDEN)
    campos.sort(key=lambda f: (orden.index(f["tabla"]), f["posicion"]))

    filas = []
    for f in campos:
        info = llaves.get((f["tabla"], f["campo"]), {"tipos": set(), "refs": []})
        nulo = '<span class="pill yes">Sí</span>' if f["nulo"] else '<span class="pill no">No</span>'
        filas.append(
            f'<tr data-table="{f["tabla"]}">'
            f'<td><span class="table-name">{f["tabla"]}</span></td>'
            f'<td><code>{f["campo"]}</code></td>'
            f'<td><span class="type">{escape(f["tipo"])}</span></td>'
            f"<td>{nulo}</td>"
            f'<td>{texto_llaves(info["tipos"], info["refs"])}</td>'
            f'<td>{escape(texto_predeterminado(f["predeterminado"]))}</td>'
            f'<td class="desc">{escape(f["descripcion"] or "")}</td>'
            "</tr>"
        )

    opciones = "".join(f'<option value="{t}">{t}</option>' for t in orden)
    tarjetas = "".join(
        f'<li><code>{t}</code><span>{escape(tablas[t])}</span></li>' for t in orden
    )

    html = DICCIONARIO.read_text(encoding="utf-8")
    # Quita la lista de tablas de una ejecución anterior antes de volver a crearla.
    html = re.sub(r'\s*<section class="panel tables-list".*?</section>', "", html, flags=re.S)
    html = re.sub(
        r'(<section class="stats".*?</section>)',
        '<section class="stats" aria-label="Resumen del diccionario">\n'
        f'    <div class="stat"><strong>{len(orden)}</strong><span>Tablas documentadas</span></div>\n'
        f'    <div class="stat"><strong>{len(campos)}</strong><span>Campos documentados</span></div>\n'
        "  </section>\n"
        '  <section class="panel tables-list" aria-label="Tablas">\n'
        f'    <ul>{tarjetas}</ul>\n'
        "  </section>",
        html,
        count=1,
        flags=re.S,
    )
    html = re.sub(
        r'(<option value="">Todas las tablas</option>).*?(</select>)',
        lambda m: m.group(1) + "\n        " + opciones + "\n      " + m.group(2),
        html, count=1, flags=re.S,
    )
    html = re.sub(
        r"<table>.*?</table>",
        "<table>\n        <thead><tr><th>TABLA</th><th>CAMPO</th><th>TIPO</th><th>NULO</th>"
        "<th>LLAVE</th><th>PREDETERMINADO</th><th>DESCRIPCIÓN</th></tr></thead>\n"
        '        <tbody id="dictionaryRows">\n          ' + "".join(filas) + "\n        </tbody>\n      </table>",
        html, count=1, flags=re.S,
    )
    html = re.sub(
        r'<p class="note">.*?</p>',
        '<p class="note"><strong>Llaves:</strong> PK = llave primaria; FK → tabla = llave foránea '
        "(apunta a otra tabla); Único = no se puede repetir. <strong>Nulo:</strong> indica si el campo "
        "puede quedar vacío. Este diccionario se genera automáticamente desde la base de datos de Bee "
        "(<code>schema.sql</code>) con <code>scripts/generar_diccionario.py</code>.</p>",
        html, count=1, flags=re.S,
    )
    estilos_extra = (
        ".tables-list{margin-bottom:22px}.tables-list ul{list-style:none;margin:0;padding:0;display:grid;"
        "grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px 18px}"
        ".tables-list li{display:flex;flex-direction:column;gap:4px;font-size:.88rem;color:var(--muted)}"
        ".tables-list code{align-self:flex-start;font-weight:700}"
        "td.desc{white-space:normal;min-width:260px;color:#475467}\n"
    )
    if ".tables-list" not in html:
        html = html.replace("</style>", estilos_extra + "</style>", 1)
    DICCIONARIO.write_text(html, encoding="utf-8")
    print(f"Diccionario actualizado: {len(orden)} tablas, {len(campos)} campos.")


if __name__ == "__main__":
    main()
