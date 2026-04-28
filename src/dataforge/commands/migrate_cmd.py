"""`dfg migrate` — aplicar migraciones SQL versionadas."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from dataforge.core.project import detect_project
from dataforge.core.ui import UI

_MIGRATIONS_TABLE = "_dataforge_migrations"

_CREATE_TABLE = f"""
CREATE TABLE IF NOT EXISTS {_MIGRATIONS_TABLE} (
    id          SERIAL PRIMARY KEY,
    filename    TEXT        NOT NULL UNIQUE,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def _load_env(root: Path) -> None:
    """Carga .env del proyecto si existe."""
    env_file = root / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file, override=False)


def _get_connection(ui: UI):
    """Abre una conexión psycopg directa (sin pool — el CLI no necesita pool)."""
    import psycopg

    url = os.environ.get("DATABASE_URL")
    if not url:
        ui.error(
            "DATABASE_URL no está definida. "
            "Copiá .env.example a .env y ajustá los valores."
        )
        raise typer.Exit(1)
    try:
        return psycopg.connect(url, autocommit=False)
    except Exception as exc:
        ui.error(f"No se pudo conectar a la base de datos: {exc}")
        raise typer.Exit(1)


def _applied_migrations(conn) -> set[str]:
    """Retorna el conjunto de filenames ya aplicados."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT filename FROM {_MIGRATIONS_TABLE};")
        return {row[0] for row in cur.fetchall()}


def _collect_migrations(migrations_dir: Path) -> list[Path]:
    """Lista archivos .sql ordenados por nombre."""
    files = sorted(migrations_dir.glob("*.sql"))
    return files


def _show_plan(pending: list[Path], applied: set[str], all_files: list[Path]) -> None:
    console = Console()
    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    table.add_column("#")
    table.add_column("Archivo")
    table.add_column("Estado")

    for f in all_files:
        if f.name in applied:
            status = "[green]✓ aplicada[/green]"
        elif f in pending:
            status = "[yellow]→ pendiente[/yellow]"
        else:
            status = "[dim]—[/dim]"
        table.add_row(f.stem[:3], f.name, status)

    console.print(table)


def migrate(
    dry_run: bool = typer.Option(False, "--dry-run", help="Mostrar qué correría sin aplicar"),
    target: str | None = typer.Option(
        None, "--to",
        help="Aplicar hasta este archivo (ej: 002_add_column.sql)",
    ),
) -> None:
    ui = UI()
    info = detect_project()
    if info is None:
        ui.error("No estás dentro de un proyecto DataForge.")
        raise typer.Exit(1)

    root = Path(info["root"])
    migrations_dir = root / "migrations"

    if not migrations_dir.is_dir():
        ui.error(f"No existe directorio de migraciones en '{root}'.")
        raise typer.Exit(1)

    all_files = _collect_migrations(migrations_dir)
    if not all_files:
        ui.info("No hay archivos .sql en migrations/.")
        raise typer.Exit(0)

    _load_env(root)

    ui.header("migrate")

    # ---------------------------------------------------------------
    # Dry-run: solo mostrar estado, sin conectar a la DB
    # ---------------------------------------------------------------
    if dry_run:
        ui.warning("Modo dry-run — no se aplica nada.")
        _show_plan(all_files, set(), all_files)
        raise typer.Exit(0)

    conn = _get_connection(ui)

    try:
        # Crear tabla de tracking si no existe
        with conn.cursor() as cur:
            cur.execute(_CREATE_TABLE)
        conn.commit()

        applied = _applied_migrations(conn)

        # Filtrar pendientes
        pending = [f for f in all_files if f.name not in applied]

        # Aplicar --to si se especificó
        if target:
            target_names = [f.name for f in all_files]
            if target not in target_names:
                ui.error(f"Archivo '{target}' no encontrado en migrations/.")
                conn.close()
                raise typer.Exit(1)
            pending = [f for f in pending if f.name <= target]

        ui.newline()
        _show_plan(pending, applied, all_files)
        ui.newline()

        if not pending:
            ui.success("Todo al día — no hay migraciones pendientes.")
            conn.close()
            raise typer.Exit(0)

        ui.info(f"{len(pending)} migración(es) para aplicar...")
        ui.newline()

        # ---------------------------------------------------------------
        # Aplicar cada migración en su propia transacción
        # ---------------------------------------------------------------
        applied_count = 0
        for mig_file in pending:
            sql = mig_file.read_text(encoding="utf-8").strip()
            if not sql:
                ui.warning(f"  {mig_file.name} — vacío, ignorado.")
                continue

            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cur.execute(
                        f"INSERT INTO {_MIGRATIONS_TABLE} (filename) VALUES (%s);",
                        (mig_file.name,),
                    )
                conn.commit()
                ui.file_created(f"{mig_file.name}")
                applied_count += 1
            except Exception as exc:
                conn.rollback()
                ui.error(f"  Error en '{mig_file.name}': {exc}")
                ui.error("  Se detuvo. Las migraciones anteriores ya fueron aplicadas.")
                conn.close()
                raise typer.Exit(1)

        ui.newline()
        ui.success(f"{applied_count} migración(es) aplicada(s).")

    finally:
        conn.close()
