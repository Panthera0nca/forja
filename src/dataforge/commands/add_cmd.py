"""`dfg add <source|entity|pipeline>` — añadir componentes (stubs v0.1)."""
import re
from datetime import datetime
from pathlib import Path

import typer

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


def _to_pascal(s: str) -> str:
    return "".join(word.capitalize() for word in s.split("_"))


def _to_table_name(name: str) -> str:
    """Convierte un nombre singular a plural para la tabla (regla simple)."""
    if name.endswith("y") and name[-2] not in "aeiou":
        return name[:-1] + "ies"
    if name.endswith(("s", "sh", "ch", "x", "z")):
        return name + "es"
    return name + "s"


@app.command("source", help="(stub) Añadir una fuente de datos (fetcher + DTO)")
def add_source(name: str = typer.Argument(..., help="Nombre snake_case de la fuente")) -> None:
    ui = UI()
    info = _require_project(ui)
    ui.header(f"add source '{name}'")
    ui.warning("Stub: próximamente generará sources/<name>.py + dtos/<name>.py")
    ui.info(f"Proyecto detectado: {info['name']} ({info['package']})")


@app.command("entity", help="Añadir una entidad (DTO + repositorio + migración)")
def add_entity(
    name: str = typer.Argument(..., help="Nombre singular de la entidad (ej: product)")
) -> None:
    ui = UI()
    info = _require_project(ui)
    root = Path(info["root"])
    package = info["package"]

    # Normalización de nombres
    entity_snake = re.sub(r"[^a-zA-Z0-9]+", "_", name).lower().strip("_")
    class_name = _to_pascal(entity_snake)
    table_name = _to_table_name(entity_snake)

    ui.header(f"Añadiendo entidad: {entity_snake}")

    context = {
        "entity_name": entity_snake,
        "class_name": class_name,
        "table_name": table_name,
        "package_name": package,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # Definir rutas de destino
    dto_path = root / "src" / package / "dtos" / f"{entity_snake}.py"
    repo_path = root / "src" / package / "repositories" / f"{entity_snake}_repository.py"
    
    # Migración: buscar el siguiente número
    migrations_dir = root / "migrations"
    migrations_dir.mkdir(exist_ok=True)
    existing = list(migrations_dir.glob("*.sql"))
    next_num = len(existing)
    migration_path = migrations_dir / f"{next_num:03d}_create_{table_name}.sql"

    # Renderizar archivos
    try:
        render_file("components/entity/dto.py.j2", dto_path, context)
        ui.file_created(str(dto_path.relative_to(root)))

        render_file("components/entity/repository.py.j2", repo_path, context)
        ui.file_created(str(repo_path.relative_to(root)))

        render_file("components/entity/migration.sql.j2", migration_path, context)
        ui.file_created(str(migration_path.relative_to(root)))

        ui.newline()
        ui.success(f"Entidad '{entity_snake}' creada")
        ui.info(f"→ DTO: {class_name} en {dto_path.relative_to(root)}")
        ui.info(f"→ Repo: {class_name}Repository en {repo_path.relative_to(root)}")
        ui.info(f"→ SQL: {migration_path.relative_to(root)}")
    except Exception as e:
        ui.error(f"Error al generar la entidad: {e}")
        raise typer.Exit(1)


@app.command("pipeline", help="(stub) Añadir un pipeline ETL")
def add_pipeline(name: str = typer.Argument(..., help="Nombre del pipeline")) -> None:
    ui = UI()
    info = _require_project(ui)
    ui.header(f"add pipeline '{name}'")
    ui.warning("Stub: próximamente generará pipelines/<name>.py con plantilla fetch→transform→load")
    ui.info(f"Proyecto detectado: {info['name']} ({info['package']})")
