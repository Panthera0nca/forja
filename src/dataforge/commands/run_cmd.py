"""`dfg run <pipeline>` — ejecutar un pipeline ETL (stub)."""
from __future__ import annotations

import typer

from dataforge.core.project import detect_project
from dataforge.core.ui import UI


def run(
    pipeline: str = typer.Argument(..., help="Nombre del pipeline"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Solo mostrar lo que haría"),
) -> None:
    ui = UI()
    info = detect_project()
    if info is None:
        ui.error("No estás dentro de un proyecto DataForge.")
        raise typer.Exit(1)

    ui.header(f"run '{pipeline}'")
    ui.warning(
        "Stub: próximamente importará src/<package>/pipelines/<pipeline>.py y ejecutará su función run()"
    )
    if dry_run:
        ui.info("(dry-run activo)")
