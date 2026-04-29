"""`dfg inspect <tabla>` — schema + estadísticas descriptivas + muestra de filas."""
from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from dataforge.core.project import detect_project
from dataforge.core.ui import UI

console = Console()


def _get_conn(ui: UI, root: Path):
    env = root / ".env"
    if env.exists():
        from dotenv import load_dotenv
        load_dotenv(env, override=False)

    url = os.environ.get("DATABASE_URL")
    if not url:
        ui.error("DATABASE_URL no definida. Copiá .env.example a .env")
        raise typer.Exit(1)
    try:
        import psycopg
        return psycopg.connect(url, autocommit=True)
    except Exception as exc:
        ui.error(f"No se pudo conectar: {exc}")
        raise typer.Exit(1)


def _table_exists(conn, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s;",
            (table,),
        )
        return cur.fetchone() is not None


def _show_schema(conn, table: str) -> list[str]:
    """Muestra columnas y tipos. Retorna lista de columnas numéricas."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position;
            """,
            (table,),
        )
        rows = cur.fetchall()

    t = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    t.add_column("Columna")
    t.add_column("Tipo")
    t.add_column("Nullable")
    t.add_column("Default", style="dim")

    numeric_types = {"integer", "bigint", "smallint", "numeric", "real",
                     "double precision", "decimal", "float"}
    numeric_cols = []

    for col, dtype, nullable, default in rows:
        t.add_row(col, dtype, "sí" if nullable == "YES" else "no", default or "—")
        if any(nt in dtype for nt in numeric_types):
            numeric_cols.append(col)

    console.print(t)
    return numeric_cols


def _show_stats(conn, table: str, numeric_cols: list[str]) -> None:
    """Estadísticas descriptivas: conteo, nulos, y stats numéricas."""
    with conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{table}";')
        total = cur.fetchone()[0]

    console.print(f"\n  [bold]Filas totales:[/bold] {total:,}")

    if not numeric_cols:
        return

    # Stats numéricas en una sola query
    parts = []
    for col in numeric_cols:
        c = f'"{col}"'
        parts += [
            f'MIN({c})', f'MAX({c})',
            f'ROUND(AVG({c})::numeric, 2)', f'COUNT({c})',
        ]

    with conn.cursor() as cur:
        cur.execute(f'SELECT {", ".join(parts)} FROM "{table}";')
        vals = cur.fetchone()

    t = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    t.add_column("Columna numérica")
    t.add_column("Min", justify="right")
    t.add_column("Max", justify="right")
    t.add_column("Avg", justify="right")
    t.add_column("No nulos", justify="right")

    for i, col in enumerate(numeric_cols):
        base = i * 4
        t.add_row(
            col,
            str(vals[base]),
            str(vals[base + 1]),
            str(vals[base + 2]),
            f"{vals[base + 3]:,} / {total:,}",
        )

    console.print(t)


def _show_sample(conn, table: str, limit: int) -> None:
    """Primeras N filas como tabla Rich."""
    with conn.cursor() as cur:
        cur.execute(f'SELECT * FROM "{table}" LIMIT %s;', (limit,))
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()

    if not rows:
        console.print("  [dim]Sin filas.[/dim]")
        return

    t = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    for col in cols:
        t.add_column(col)

    for row in rows:
        t.add_row(*[str(v) if v is not None else "[dim]NULL[/dim]" for v in row])

    console.print(t)


def inspect(
    table: str = typer.Argument(..., help="Nombre de la tabla a inspeccionar"),
    limit: int = typer.Option(10, "--limit", "-n", help="Filas de muestra a mostrar"),
    stats: bool = typer.Option(True, "--stats/--no-stats", help="Mostrar estadísticas descriptivas"),
) -> None:
    ui = UI()
    info = detect_project()
    if info is None:
        ui.error("No estás dentro de un proyecto DataForge.")
        raise typer.Exit(1)

    conn = _get_conn(ui, Path(info["root"]))

    if not _table_exists(conn, table):
        ui.error(f"Tabla '{table}' no existe en el schema público.")
        conn.close()
        raise typer.Exit(1)

    ui.header(f"inspect · {table}")

    console.print("\n[bold]Schema[/bold]")
    numeric_cols = _show_schema(conn, table)

    if stats:
        console.print("\n[bold]Estadísticas[/bold]")
        _show_stats(conn, table, numeric_cols)

    console.print(f"\n[bold]Muestra ({limit} filas)[/bold]")
    _show_sample(conn, table, limit)

    console.print()
    conn.close()
