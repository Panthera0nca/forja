"""`dfg run <pipeline>` — ejecutar un pipeline del proyecto."""
from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path

import typer

from dataforge.core.project import detect_project
from dataforge.core.ui import UI


def _list_pipelines(src_root: Path, package: str) -> list[str]:
    pipelines_dir = src_root / package / "pipelines"
    if not pipelines_dir.is_dir():
        return []
    return [
        f.stem for f in sorted(pipelines_dir.glob("*.py"))
        if f.stem != "__init__"
    ]


def run(
    pipeline: str = typer.Argument(..., help="Nombre del pipeline (ej: training, ingestion)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Mostrar qué correría sin ejecutar"),
    list_: bool = typer.Option(False, "--list", "-l", help="Listar pipelines disponibles"),
) -> None:
    ui = UI()
    info = detect_project()
    if info is None:
        ui.error("No estás dentro de un proyecto DataForge.")
        raise typer.Exit(1)

    root = Path(info["root"])
    package = info["package"]
    src_root = root / "src"

    # --list: mostrar pipelines disponibles y salir
    if list_:
        available = _list_pipelines(src_root, package)
        ui.header("Pipelines disponibles")
        if available:
            for p in available:
                ui.info(f"  dfg run {p}")
        else:
            ui.warning(f"No se encontraron pipelines en src/{package}/pipelines/")
        raise typer.Exit(0)

    module_path = f"{package}.pipelines.{pipeline}"
    pipeline_file = src_root / package / "pipelines" / f"{pipeline}.py"

    ui.header(f"run '{pipeline}'")

    # --dry-run: solo mostrar qué correría
    if dry_run:
        ui.info(f"  módulo : {module_path}")
        ui.info(f"  archivo: {pipeline_file.relative_to(root) if pipeline_file.exists() else '(no encontrado)'}")
        ui.info(f"  función: {module_path}.run()")
        raise typer.Exit(0)

    # Verificar que el archivo existe antes de intentar importar
    if not pipeline_file.exists():
        available = _list_pipelines(src_root, package)
        ui.error(f"Pipeline '{pipeline}' no encontrado en src/{package}/pipelines/")
        if available:
            ui.info(f"  Disponibles: {', '.join(available)}")
        raise typer.Exit(1)

    # Cargar .env del proyecto
    env_file = root / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file, override=False)

    # Agregar src/ al path para que el import funcione
    src_str = str(src_root)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

    # Importar el módulo
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        ui.error(f"No se pudo importar '{module_path}': {exc}")
        raise typer.Exit(1)

    # Verificar que tiene run()
    if not hasattr(module, "run"):
        ui.error(f"El módulo '{module_path}' no tiene una función run().")
        raise typer.Exit(1)

    # Ejecutar
    ui.info(f"→ {module_path}.run()")
    ui.newline()
    try:
        module.run()
    except Exception:
        ui.newline()
        ui.error("El pipeline terminó con error:")
        traceback.print_exc()
        raise typer.Exit(1)
