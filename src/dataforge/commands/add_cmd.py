"""`dfg add <source|entity|pipeline>` — añadir componentes al proyecto."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from dataforge.core.entity_parser import parse, to_template_context
from dataforge.core.project import detect_project
from dataforge.core.templates import render_file
from dataforge.core.ui import UI

app = typer.Typer(no_args_is_help=True, help="Añadir componentes al proyecto")


def _require_project(ui: UI) -> dict:
    info = detect_project()
    if info is None:
        ui.error("No estás dentro de un proyecto DataForge. Usa 'dfg init' primero.")
        raise typer.Exit(1)
    return info


def _show_inference_table(context: dict) -> None:
    """Muestra una tabla con los campos inferidos antes de generar."""
    console = Console()
    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    table.add_column("Campo")
    table.add_column("Tipo SQL")
    table.add_column("Tipo Python")
    table.add_column("Nota", style="dim")

    for f in context["dto_fields"]:
        # Buscar sql_def correspondiente
        sql_def = next(
            (s["sql_def"] for s in context["sql_fields"] if s["name"] == f["name"]),
            "—",
        )
        note = f["comment"] or ""
        table.add_row(f["name"], sql_def, f["python_type"], note)

    console.print(table)


@app.command("entity", help="Añadir una entidad: 'Cliente (nombre, dirección, teléfono)'")
def add_entity(
    definition: str = typer.Argument(
        ...,
        help="Nombre o definición completa: 'Cliente (nombre, teléfono)' o solo 'cliente'",
    ),
    no_confirm: bool = typer.Option(
        False, "--yes", "-y", help="No pedir confirmación antes de generar"
    ),
) -> None:
    ui = UI()
    info = _require_project(ui)
    root = Path(info["root"])
    package = info["package"]
    domain = info.get("domain", "generic")

    # ----------------------------------------------------------------
    # Modo interactivo si solo se pasó un nombre sin campos
    # ----------------------------------------------------------------
    if "(" not in definition:
        ui.header(f"Añadiendo entidad: {definition.strip()}")
        ui.info("No se especificaron campos. Ingrésalos a continuación.")
        ui.info("Formato: nombre, dirección, teléfono, cliente_id, estado, ...")
        ui.info("(Enter vacío para usar solo 'id, created_at, updated_at')")
        raw_fields = typer.prompt("  Campos", default="").strip()
        if raw_fields:
            definition = f"{definition.strip()} ({raw_fields})"

    # ----------------------------------------------------------------
    # Parsear y mostrar inferencia
    # ----------------------------------------------------------------
    entity = parse(definition, domain=domain)
    context = to_template_context(
        entity, package_name=package,
        created_at=datetime.now().strftime("%Y-%m-%d"),
    )

    ui.header(f"Entidad: {entity.class_name}  →  tabla '{entity.table_name}'")
    ui.newline()
    _show_inference_table(context)

    if entity.fk_fields:
        ui.newline()
        for fk in context["fk_constraints"]:
            ui.info(f"  FK: {fk['field']} → {fk['ref_table']}(id)")

    if entity.enum_fields:
        ui.newline()
        for f in entity.enum_fields:
            ui.info(f"  ENUM {f.enum_var}: {', '.join(f.enum_values)}")

    ui.newline()

    if not no_confirm:
        ok = typer.confirm("  ¿Generar con esta inferencia?", default=True)
        if not ok:
            ui.info("Cancelado.")
            raise typer.Exit(0)

    # ----------------------------------------------------------------
    # Rutas de destino
    # ----------------------------------------------------------------
    dto_path  = root / "src" / package / "dtos" / f"{entity.snake_name}.py"
    repo_path = root / "src" / package / "repositories" / f"{entity.snake_name}_repository.py"

    migrations_dir = root / "migrations"
    migrations_dir.mkdir(exist_ok=True)
    next_num = len(list(migrations_dir.glob("*.sql")))
    migration_path = migrations_dir / f"{next_num:03d}_create_{entity.table_name}.sql"

    # ----------------------------------------------------------------
    # Renderizar
    # ----------------------------------------------------------------
    try:
        render_file("components/entity/dto.py.j2", dto_path, context)
        ui.file_created(str(dto_path.relative_to(root)))

        render_file("components/entity/repository.py.j2", repo_path, context)
        ui.file_created(str(repo_path.relative_to(root)))

        render_file("components/entity/migration.sql.j2", migration_path, context)
        ui.file_created(str(migration_path.relative_to(root)))

        ui.newline()
        ui.success(f"Entidad '{entity.snake_name}' creada")
        ui.info(f"→ DTO:  {entity.class_name}  en  {dto_path.relative_to(root)}")
        ui.info(f"→ Repo: {entity.class_name}Repository  en  {repo_path.relative_to(root)}")
        ui.info(f"→ SQL:  {migration_path.relative_to(root)}")

    except Exception as e:
        ui.error(f"Error al generar la entidad: {e}")
        raise typer.Exit(1)


@app.command("source", help="Añadir una fuente de datos al proyecto")
def add_source(
    name: str = typer.Argument(..., help="Nombre snake_case de la fuente (ej: api_clima, csv_ventas)"),
    no_confirm: bool = typer.Option(False, "--yes", "-y", help="No pedir confirmación"),
) -> None:
    ui = UI()
    info = _require_project(ui)
    root = Path(info["root"])
    package = info["package"]

    snake_name = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    class_name = "".join(w.capitalize() for w in snake_name.split("_"))

    dest = root / "src" / package / "sources" / f"{snake_name}.py"

    ui.header(f"add source '{snake_name}'")
    ui.key_value("Clase",   f"{class_name}Source")
    ui.key_value("Archivo", str(dest.relative_to(root)))
    ui.newline()

    if dest.exists():
        ui.error(f"'{dest.relative_to(root)}' ya existe.")
        raise typer.Exit(1)

    if not no_confirm:
        ok = typer.confirm("  ¿Generar?", default=True)
        if not ok:
            ui.info("Cancelado.")
            raise typer.Exit(0)

    context = {
        "package_name": package,
        "snake_name":   snake_name,
        "class_name":   class_name,
        "created_at":   datetime.now().strftime("%Y-%m-%d"),
    }
    try:
        render_file("components/source/source.py.j2", dest, context)
        ui.file_created(str(dest.relative_to(root)))
        ui.newline()
        ui.success(f"Source '{snake_name}' creado")
        ui.info(f"→ Implementá fetch() en {dest.relative_to(root)}")
        ui.info(f"→ Definí la entidad con: dfg add entity \"{class_name} (campo1, campo2, ...)\"")
    except Exception as e:
        ui.error(f"Error al generar el source: {e}")
        raise typer.Exit(1)


@app.command("exporter", help="Añadir un exporter al proyecto (--format sql|excel)")
def add_exporter(
    name: str = typer.Argument(..., help="Nombre snake_case del exporter (ej: ventas, pacientes)"),
    fmt: str = typer.Option("excel", "--format", "-f", help="Formato de salida: sql | excel"),
    no_confirm: bool = typer.Option(False, "--yes", "-y", help="No pedir confirmación"),
) -> None:
    ui = UI()
    info = _require_project(ui)
    root = Path(info["root"])
    package = info["package"]

    if fmt not in ("sql", "excel"):
        ui.error("Formato inválido. Usá --format sql o --format excel")
        raise typer.Exit(1)

    snake_name = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    class_name = "".join(w.capitalize() for w in snake_name.split("_"))
    suffix = "sql" if fmt == "sql" else "excel"
    filename = f"{snake_name}_{suffix}.py"
    dest = root / "src" / package / "exporters" / filename

    ui.header(f"add exporter '{snake_name}' [{fmt}]")
    ui.key_value("Clase",   f"{class_name}{'Sql' if fmt == 'sql' else 'Excel'}Exporter")
    ui.key_value("Archivo", str(dest.relative_to(root)))
    ui.key_value("Salida",  f"exports/{snake_name}.{'sql' if fmt == 'sql' else 'xlsx'}")
    ui.newline()

    if dest.exists():
        ui.error(f"'{dest.relative_to(root)}' ya existe.")
        raise typer.Exit(1)

    if not no_confirm:
        ok = typer.confirm("  ¿Generar?", default=True)
        if not ok:
            ui.info("Cancelado.")
            raise typer.Exit(0)

    template = f"components/exporter/{'sql' if fmt == 'sql' else 'excel'}_exporter.py.j2"
    context = {
        "package_name": package,
        "snake_name":   snake_name,
        "class_name":   class_name,
        "created_at":   datetime.now().strftime("%Y-%m-%d"),
    }
    try:
        render_file(template, dest, context)
        ui.file_created(str(dest.relative_to(root)))
        ui.newline()
        ui.success(f"Exporter '{snake_name}' [{fmt}] creado")
        ui.info(f"→ Usalo en un pipeline: exporter.export(records, Path('exports/{snake_name}.{'sql' if fmt == 'sql' else 'xlsx'}'))")
        if fmt == "excel":
            ui.info("→ Requiere: pip install openpyxl")
    except Exception as e:
        ui.error(f"Error al generar el exporter: {e}")
        raise typer.Exit(1)


@app.command("pipeline", help="Añadir un pipeline al proyecto")
def add_pipeline(
    name: str = typer.Argument(..., help="Nombre snake_case del pipeline (ej: ingestion, daily_report)"),
    no_confirm: bool = typer.Option(False, "--yes", "-y", help="No pedir confirmación"),
) -> None:
    ui = UI()
    info = _require_project(ui)
    root = Path(info["root"])
    package = info["package"]

    snake_name = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    class_name = "".join(w.capitalize() for w in snake_name.split("_"))

    dest = root / "src" / package / "pipelines" / f"{snake_name}.py"

    ui.header(f"add pipeline '{snake_name}'")
    ui.key_value("Archivo", str(dest.relative_to(root)))
    ui.key_value("Ejecutar con", f"dfg run {snake_name}")
    ui.newline()

    if dest.exists():
        ui.error(f"'{dest.relative_to(root)}' ya existe.")
        raise typer.Exit(1)

    if not no_confirm:
        ok = typer.confirm("  ¿Generar?", default=True)
        if not ok:
            ui.info("Cancelado.")
            raise typer.Exit(0)

    context = {
        "package_name": package,
        "snake_name":   snake_name,
        "class_name":   class_name,
        "created_at":   datetime.now().strftime("%Y-%m-%d"),
    }
    try:
        render_file("components/pipeline/pipeline.py.j2", dest, context)
        ui.file_created(str(dest.relative_to(root)))
        ui.newline()
        ui.success(f"Pipeline '{snake_name}' creado")
        ui.info(f"→ Implementá run() en {dest.relative_to(root)}")
        ui.info(f"→ Ejecutá con: dfg run {snake_name}")
    except Exception as e:
        ui.error(f"Error al generar el pipeline: {e}")
        raise typer.Exit(1)
