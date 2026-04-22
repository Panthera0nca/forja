"""Entrypoint del CLI DataForge."""
from __future__ import annotations

import typer

from dataforge import __version__
from dataforge.commands import (
    add_cmd,
    fetch_cmd,
    init_cmd,
    inspect_cmd,
    migrate_cmd,
    run_cmd,
    status_cmd,
)
from dataforge.core.ui import UI


app = typer.Typer(
    name="dataforge",
    help="🗄️  CLI para proyectos de datos en capas (Sources/DTOs/Repositories/Services)",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=True,
)

# Comandos de nivel simple
app.command(name="init", help="Crear un nuevo proyecto ETL")(init_cmd.init)
app.command(name="status", help="Mostrar info del proyecto actual")(status_cmd.status)
app.command(name="fetch", help="(stub) Ejecutar un fetcher")(fetch_cmd.fetch)
app.command(name="run", help="(stub) Ejecutar un pipeline")(run_cmd.run)
app.command(name="inspect", help="(stub) Inspeccionar una tabla de Postgres")(inspect_cmd.inspect)
app.command(name="migrate", help="(stub) Aplicar migraciones SQL")(migrate_cmd.migrate)

# add tiene subcomandos (source / entity / pipeline)
app.add_typer(add_cmd.app, name="add", help="Añadir componentes al proyecto")


@app.command(help="Mostrar versión")
def version() -> None:
    UI().success(f"DataForge v{__version__}")


if __name__ == "__main__":
    app()
