"""`dfg init <nombre>` — generar un proyecto ETL nuevo."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import typer

from dataforge.core.templates import render_template
from dataforge.core.ui import UI


PACKAGE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _to_package_name(name: str) -> str:
    """Convierte un nombre de proyecto a package Python válido."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name).lower().strip("_")
    if not slug:
        slug = "project"
    if slug[0].isdigit():
        slug = f"p_{slug}"
    return slug


def init(
    name: str = typer.Argument(..., help="Nombre del proyecto (también nombre de carpeta)"),
    project_type: str = typer.Option(
        "etl", "--type", "-t",
        help="Tipo de proyecto. Disponible: etl",
    ),
    package: str | None = typer.Option(
        None, "--package", "-p",
        help="Nombre del package Python (default: derivado del nombre)",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Sobrescribir si existe"),
) -> None:
    ui = UI()
    dest = Path(name)

    if dest.exists() and not force:
        ui.error(f"El directorio '{name}' ya existe. Usa --force para sobrescribir.")
        raise typer.Exit(1)

    templates_available = {"etl"}
    if project_type not in templates_available:
        ui.error(
            f"Tipo '{project_type}' no disponible. "
            f"Opciones: {', '.join(sorted(templates_available))}"
        )
        raise typer.Exit(1)

    pkg = package or _to_package_name(name)
    if not PACKAGE_NAME_RE.match(pkg):
        ui.error(f"Package '{pkg}' inválido. Debe ser snake_case empezando por letra.")
        raise typer.Exit(1)

    context = {
        "project_name": name,
        "package_name": pkg,
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "python_version": "3.12",
        "postgres_image": "postgres:16-alpine",
    }

    ui.header(f"Creando proyecto '{name}' [{project_type}]")
    ui.key_value("Package", pkg)
    ui.newline()

    created = render_template(f"{project_type}_project", dest, context)
    for path in created:
        try:
            rel = path.relative_to(Path.cwd())
        except ValueError:
            rel = path
        ui.file_created(str(rel))

    ui.newline()
    ui.success(f"Proyecto '{name}' creado — {len(created)} archivos")
    ui.info(f"cd {name}")
    ui.info("docker compose up -d         # levantar Postgres local")
    ui.info("pip install -e .             # instalar el proyecto")
    ui.info("dfg status                   # verificar detección del proyecto")
    ui.newline()
