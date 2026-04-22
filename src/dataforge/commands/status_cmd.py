"""`dfg status` — info del proyecto actual."""
from __future__ import annotations

import typer

from dataforge.core.project import detect_project
from dataforge.core.ui import UI


def status() -> None:
    ui = UI()
    info = detect_project()

    ui.header("Estado del Proyecto")

    if info is None:
        ui.warning("No se detectó un proyecto DataForge en este directorio o padres.")
        ui.info("Usa 'dfg init <nombre>' para crear uno.")
        raise typer.Exit(1)

    ui.key_value("Nombre", info["name"])
    ui.key_value("Package", info["package"])
    ui.key_value("Tipo", info["type"])
    ui.key_value("Raíz", str(info["root"]))
    ui.key_value("Fuentes", str(info["sources_count"]))
    ui.key_value("Pipelines", str(info["pipelines_count"]))
    ui.key_value("Migraciones", "✓" if info["has_migrations"] else "—")
    ui.key_value("Docker compose", "✓" if info["has_docker"] else "—")
    ui.newline()
