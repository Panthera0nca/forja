"""`dfg export <exporter>` — correr un exporter y escribir el archivo de salida."""
from __future__ import annotations

import importlib
import inspect
import os
import sys
import traceback
from pathlib import Path

import typer

from dataforge.core.project import detect_project
from dataforge.core.ui import UI


def _list_exporters(src_root: Path, package: str) -> list[str]:
    exporters_dir = src_root / package / "exporters"
    if not exporters_dir.is_dir():
        return []
    return [
        f.stem for f in sorted(exporters_dir.glob("*.py"))
        if f.stem not in ("__init__", "base")
    ]


def _find_exporter_class(module):
    """Encuentra la primera clase con export() en el módulo."""
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ == module.__name__:
            if hasattr(obj, "export") and callable(getattr(obj, "export")):
                return obj
    return None


def _fetch_records(table: str, root: Path, limit: int | None) -> list[dict]:
    """Consulta todos los registros de una tabla vía psycopg."""
    env = root / ".env"
    if env.exists():
        from dotenv import load_dotenv
        load_dotenv(env, override=False)

    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL no definida. Copiá .env.example a .env")

    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            sql = f'SELECT * FROM "{table}"'
            if limit:
                sql += f" LIMIT {limit}"
            cur.execute(sql)
            return cur.fetchall()


def export(
    exporter: str = typer.Argument(..., help="Nombre del exporter (ej: ordenes_sql, productos_excel)"),
    dest: str | None = typer.Option(None, "--dest", "-o", help="Ruta de salida (default: exports/<nombre>)"),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Limitar registros (útil para testing)"),
    no_db: bool = typer.Option(False, "--no-db", help="No consultar DB — pasar lista vacía (test del exporter)"),
    list_: bool = typer.Option(False, "--list", "-l", help="Listar exporters disponibles"),
) -> None:
    ui = UI()
    info = detect_project()
    if info is None:
        ui.error("No estás dentro de un proyecto DataForge.")
        raise typer.Exit(1)

    root = Path(info["root"])
    package = info["package"]
    src_root = root / "src"

    if list_:
        available = _list_exporters(src_root, package)
        ui.header("Exporters disponibles")
        if available:
            for e in available:
                ui.info(f"  dfg export {e}")
        else:
            ui.warning(f"No se encontraron exporters en src/{package}/exporters/")
        raise typer.Exit(0)

    module_path = f"{package}.exporters.{exporter}"
    exporter_file = src_root / package / "exporters" / f"{exporter}.py"

    ui.header(f"export '{exporter}'")

    if not exporter_file.exists():
        available = _list_exporters(src_root, package)
        ui.error(f"Exporter '{exporter}' no encontrado en src/{package}/exporters/")
        if available:
            ui.info(f"  Disponibles: {', '.join(available)}")
        raise typer.Exit(1)

    src_str = str(src_root)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        ui.error(f"No se pudo importar '{module_path}': {exc}")
        raise typer.Exit(1)

    cls = _find_exporter_class(module)
    if cls is None:
        ui.error(f"No se encontró ninguna clase con export() en '{module_path}'.")
        raise typer.Exit(1)

    instance = cls()
    table = getattr(instance, "table", None)

    # Determinar extensión por el nombre de la clase
    cls_name = cls.__name__.lower()
    ext = "xlsx" if "excel" in cls_name else "sql"

    # Ruta de destino
    out_path = Path(dest) if dest else root / "exports" / f"{getattr(instance, 'name', exporter)}.{ext}"

    ui.key_value("Clase",  cls.__name__)
    ui.key_value("Tabla",  table or "— (definí `table` en la clase)")
    ui.key_value("Salida", str(out_path.relative_to(root) if out_path.is_relative_to(root) else out_path))
    if limit:
        ui.key_value("Límite", str(limit))
    ui.newline()

    # Obtener registros
    records: list = []
    if no_db:
        ui.warning("--no-db activo — exportando lista vacía.")
    elif table:
        try:
            ui.info(f"Consultando tabla '{table}'...")
            records = _fetch_records(table, root, limit)
            ui.info(f"  {len(records)} registro(s) obtenidos.")
        except Exception as exc:
            ui.error(f"Error al consultar la DB: {exc}")
            raise typer.Exit(1)
    else:
        ui.warning("La clase no tiene `table` definida — exportando lista vacía.")
        ui.info("  Definí `table = 'nombre_tabla'` en la clase o implementá tu propia lógica de carga.")

    ui.newline()

    # Exportar
    try:
        created = instance.export(records, out_path)
        ui.success(f"Archivo exportado: {created}")
        size_kb = created.stat().st_size / 1024
        ui.info(f"  Tamaño: {size_kb:.1f} KB  |  Registros: {len(records)}")
    except RuntimeError as exc:
        ui.error(str(exc))
        raise typer.Exit(1)
    except Exception:
        ui.error("El exporter terminó con error:")
        traceback.print_exc()
        raise typer.Exit(1)
