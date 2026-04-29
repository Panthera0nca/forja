"""`dfg fetch <source>` — correr un source en aislamiento para debugging."""
from __future__ import annotations

import importlib
import inspect
import sys
import traceback
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from dataforge.core.project import detect_project
from dataforge.core.ui import UI

console = Console()


def _list_sources(src_root: Path, package: str) -> list[str]:
    sources_dir = src_root / package / "sources"
    if not sources_dir.is_dir():
        return []
    return [
        f.stem for f in sorted(sources_dir.glob("*.py"))
        if f.stem not in ("__init__", "base")
    ]


def _find_source_class(module):
    """Encuentra la primera clase con un método fetch() en el módulo."""
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ == module.__name__:
            if hasattr(obj, "fetch") and callable(getattr(obj, "fetch")):
                return obj
    return None


def _display_records(records: list, limit: int) -> None:
    sample = list(records)[:limit]
    if not sample:
        console.print("  [dim]Sin registros.[/dim]")
        return

    first = sample[0]

    # Dict o Pydantic → tabla Rich
    if isinstance(first, dict):
        keys = list(first.keys())
    elif hasattr(first, "model_dump"):
        keys = list(first.model_dump().keys())
    else:
        # Fallback: imprimir como texto
        for i, r in enumerate(sample):
            console.print(f"  [{i}] {r}")
        return

    t = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    for k in keys:
        t.add_column(str(k))

    for record in sample:
        row = record if isinstance(record, dict) else record.model_dump()
        t.add_row(*[str(row.get(k, "")) for k in keys])

    console.print(t)


def fetch(
    source: str = typer.Argument(..., help="Nombre del source (ej: api_clima, csv_ventas)"),
    limit: int = typer.Option(10, "--limit", "-n", help="Máximo de registros a mostrar"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Mostrar qué correría sin ejecutar"),
    list_: bool = typer.Option(False, "--list", "-l", help="Listar sources disponibles"),
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
        available = _list_sources(src_root, package)
        ui.header("Sources disponibles")
        if available:
            for s in available:
                ui.info(f"  dfg fetch {s}")
        else:
            ui.warning(f"No se encontraron sources en src/{package}/sources/")
        raise typer.Exit(0)

    module_path = f"{package}.sources.{source}"
    source_file = src_root / package / "sources" / f"{source}.py"

    ui.header(f"fetch '{source}'")

    if dry_run:
        ui.info(f"  módulo : {module_path}")
        ui.info(f"  archivo: {source_file.relative_to(root) if source_file.exists() else '(no encontrado)'}")
        ui.info(f"  límite : {limit} registros")
        raise typer.Exit(0)

    if not source_file.exists():
        available = _list_sources(src_root, package)
        ui.error(f"Source '{source}' no encontrado en src/{package}/sources/")
        if available:
            ui.info(f"  Disponibles: {', '.join(available)}")
        raise typer.Exit(1)

    env_file = root / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file, override=False)

    src_str = str(src_root)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        ui.error(f"No se pudo importar '{module_path}': {exc}")
        raise typer.Exit(1)

    cls = _find_source_class(module)
    if cls is None:
        ui.error(f"No se encontró ninguna clase con fetch() en '{module_path}'.")
        raise typer.Exit(1)

    ui.info(f"→ {cls.__name__}.fetch()  (límite: {limit})")
    ui.newline()

    try:
        instance = cls()
        records = list(instance.fetch())
        total = len(records)
        _display_records(records, limit)
        ui.newline()
        ui.success(f"{total} registro(s) obtenidos" + (f" — mostrando {min(limit, total)}" if total > limit else ""))
    except NotImplementedError:
        ui.warning("fetch() aún no está implementado en este source.")
        ui.info(f"→ Editá {source_file.relative_to(root)} y completá el método fetch()")
    except Exception:
        ui.newline()
        ui.error("El source terminó con error:")
        traceback.print_exc()
        raise typer.Exit(1)
