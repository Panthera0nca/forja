"""`dfg inspect <tabla>` — inspeccionar una tabla en Postgres (stub)."""
from __future__ import annotations

import typer

from dataforge.core.project import detect_project
from dataforge.core.ui import UI


def inspect(
    table: str = typer.Argument(..., help="Nombre de la tabla a inspeccionar"),
    limit: int = typer.Option(10, "--limit", "-n", help="Número de filas a mostrar"),
) -> None:
    ui = UI()
    info = detect_project()
    if info is None:
        ui.error("No estás dentro de un proyecto DataForge.")
        raise typer.Exit(1)

    ui.header(f"inspect '{table}' (limit={limit})")
    ui.warning(
        "Stub: próximamente se conectará a Postgres (vía DATABASE_URL) "
        "y mostrará schema + primeras N filas"
    )
