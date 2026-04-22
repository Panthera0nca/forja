"""`dfg migrate` — aplicar migraciones SQL (stub)."""
from __future__ import annotations

import typer

from dataforge.core.project import detect_project
from dataforge.core.ui import UI


def migrate(
    dry_run: bool = typer.Option(False, "--dry-run", help="Solo mostrar qué correría"),
) -> None:
    ui = UI()
    info = detect_project()
    if info is None:
        ui.error("No estás dentro de un proyecto DataForge.")
        raise typer.Exit(1)

    ui.header("migrate")
    ui.warning(
        "Stub: próximamente ejecutará las *.sql de migrations/ en orden, "
        "registrando en tabla _dataforge_migrations"
    )
    if dry_run:
        ui.info("(dry-run activo)")
