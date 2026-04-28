"""`dfg fetch <source>` — ejecutar un fetcher (stub)."""
from __future__ import annotations

import typer

from dataforge.core.project import detect_project
from dataforge.core.ui import UI


def fetch(
    source: str = typer.Argument(..., help="Nombre de la fuente a ejecutar"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Solo mostrar lo que haría"),
) -> None:
    ui = UI()
    info = detect_project()
    if info is None:
        ui.error("No estás dentro de un proyecto DataForge.")
        raise typer.Exit(1)

    ui.header(f"fetch '{source}'")
    ui.warning(
        "Stub: próximamente importará src/<package>/sources/<source>.py y ejecutará su función fetch()"
    )
    if dry_run:
        ui.info("(dry-run activo)")
