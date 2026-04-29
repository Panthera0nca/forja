"""Entrypoint del CLI DataForge."""
from __future__ import annotations

import typer

from dataforge import __version__
from dataforge.commands import (
    add_cmd,
    classify_cmd,
    clean_cmd,
    doctor_cmd,
    export_cmd,
    fetch_cmd,
    init_cmd,
    inspect_cmd,
    migrate_cmd,
    plugins_cmd,
    run_cmd,
    status_cmd,
    upgrade_cmd,
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
app.command(name="init", help="Crear un nuevo proyecto (wizard de dominio + arquitectura)")(init_cmd.init)
app.command(name="classify", help="Clasificar el dominio de un proyecto sin crear archivos")(classify_cmd.classify)
app.command(name="status", help="Mostrar info del proyecto actual")(status_cmd.status)
app.command(name="doctor", help="Diagnóstico de salud del proyecto")(doctor_cmd.doctor)
app.command(name="fetch", help="Correr un source en aislamiento para debugging")(fetch_cmd.fetch)
app.command(name="run", help="Ejecutar un pipeline del proyecto")(run_cmd.run)
app.command(name="inspect", help="Schema + estadísticas + muestra de una tabla")(inspect_cmd.inspect)
app.command(name="export", help="Correr un exporter y escribir el archivo de salida")(export_cmd.export)
app.command(name="migrate", help="Aplicar migraciones SQL versionadas")(migrate_cmd.migrate)
app.command(name="upgrade", help="Actualizar proyecto a la versión actual de forja")(upgrade_cmd.upgrade)
app.command(name="plugins", help="Listar plugins de forja instalados")(plugins_cmd.plugins)

# add tiene subcomandos (source / entity / pipeline)
app.add_typer(add_cmd.app, name="add", help="Añadir componentes al proyecto")

# clean tiene subcomandos (project / data)
app.add_typer(clean_cmd.app, name="clean", help="Motor de limpieza recursivo (RQM)")


@app.command(help="Mostrar versión")
def version() -> None:
    UI().success(f"DataForge v{__version__}")


if __name__ == "__main__":
    app()
