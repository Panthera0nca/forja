"""`dfg clean` — motor de limpieza recursivo con modelo RQM.

Subcomandos:
  dfg clean project  — estructura de archivos (migraciones, DTOs, repos)
  dfg clean data     — calidad de datos en PostgreSQL
  dfg clean          — ambos

El motor corre sobre cualquier ruta — incluyendo el propio dfg.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.tree import Tree
from rich import print as rprint

from dataforge.core.cleaner import (
    CleaningNode,
    DataCleaner,
    Issue,
    IssueType,
    ProjectCleaner,
    Severity,
)
from dataforge.core.ui import UI

app = typer.Typer(
    no_args_is_help=False,
    invoke_without_command=True,
    help="Motor de limpieza recursivo (proyecto + datos)",
)

console = Console()


# ---------------------------------------------------------------------------
# Helpers de visualización
# ---------------------------------------------------------------------------

_SCORE_COLORS = {
    "excelente": "bold green",
    "bueno":     "green",
    "regular":   "yellow",
    "deficiente":"red",
    "crítico":   "bold red",
}

_SEV_COLORS = {
    Severity.CRITICAL: "bold red",
    Severity.HIGH:     "red",
    Severity.MEDIUM:   "yellow",
    Severity.LOW:      "dim",
}


def _score_bar(score: float, width: int = 16) -> str:
    filled = int(score * width)
    bar = "█" * filled + "░" * (width - filled)
    color = "green" if score >= 0.75 else ("yellow" if score >= 0.50 else "red")
    return f"[{color}]{bar}[/{color}] {score*100:.0f}%"


def _render_tree(node: CleaningNode, rich_tree: Tree, show_ok: bool = False) -> None:
    """Renderiza el árbol de calidad recursivamente."""
    score = node.quality_score()
    label = node.score_label()
    color = _SCORE_COLORS.get(label, "white")
    issues = node.all_issues()

    summary = (
        f"[bold]{node.name}[/bold]  "
        f"{_score_bar(score)}  "
        f"[{color}]{label}[/{color}]"
    )
    if issues:
        summary += f"  [dim]({len(issues)} issue{'s' if len(issues) > 1 else ''})[/dim]"

    branch = rich_tree.add(summary)

    # Issues directos del nodo
    for issue in node.issues:
        sev_color = _SEV_COLORS[issue.severity]
        icon = issue.severity_icon
        fix_hint = f"  [dim]→ {issue.fix_hint}[/dim]" if issue.fix_hint else ""
        branch.add(
            f"{icon} [{sev_color}]{issue.message}[/{sev_color}]"
            f"  [dim]{issue.location}[/dim]{fix_hint}"
        )

    # Hijos con issues (o todos si show_ok)
    for child in node.children:
        child_issues = child.all_issues()
        if child_issues or show_ok:
            _render_tree(child, branch, show_ok)


def _print_summary(node: CleaningNode) -> None:
    all_issues = node.all_issues()
    by_severity: dict[Severity, int] = {}
    for issue in all_issues:
        by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1

    score = node.quality_score()
    label = node.score_label()
    color = _SCORE_COLORS.get(label, "white")

    console.print()
    console.rule("[bold]Resumen de calidad[/bold]")
    console.print(
        f"  Score global:  {_score_bar(score)}  "
        f"[{color}]{label.upper()}[/{color}]"
    )
    console.print()

    if all_issues:
        for sev in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW):
            count = by_severity.get(sev, 0)
            if count:
                sev_color = _SEV_COLORS[sev]
                console.print(
                    f"  [{sev_color}]{sev.value.upper():10}[/{sev_color}]  {count} issue{'s' if count>1 else ''}"
                )
        fixable = len(node.fixable_issues())
        if fixable:
            console.print()
            console.print(f"  [green]{fixable} issue(s) reparables automáticamente[/green]  →  usa [bold]--fix[/bold]")
    else:
        console.print("  [green]✓ Sin issues detectados[/green]")
    console.print()


# ---------------------------------------------------------------------------
# Subcomando: project
# ---------------------------------------------------------------------------

@app.command("project")
def clean_project(
    path: Optional[Path] = typer.Argument(
        None, help="Ruta del proyecto (default: directorio actual)"
    ),
    fix: bool = typer.Option(False, "--fix", help="Aplicar fixes automáticos"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Mostrar fixes sin aplicar"),
    show_ok: bool = typer.Option(False, "--show-ok", help="Mostrar nodos sin issues"),
) -> None:
    """Escanea la estructura del proyecto: migraciones, DTOs, repositorios."""
    ui = UI()
    root = (path or Path.cwd()).resolve()

    ui.header(f"Limpieza de proyecto: {root.name}")
    ui.info(f"  Ruta: {root}")
    ui.newline()

    cleaner = ProjectCleaner(root)
    report = cleaner.scan()

    tree = Tree(
        f"[bold cyan]{root.name}[/bold cyan]  {_score_bar(report.quality_score())}"
    )
    _render_tree(report, tree, show_ok=show_ok)
    console.print(tree)
    _print_summary(report)

    if fix or dry_run:
        actions = cleaner.fix(report, dry_run=dry_run)
        if actions:
            prefix = "[DRY-RUN] " if dry_run else ""
            ui.header(f"{prefix}Acciones de reparación")
            for action in actions:
                ui.file_created(action)
        else:
            ui.info("No hay acciones automáticas disponibles.")


# ---------------------------------------------------------------------------
# Subcomando: data
# ---------------------------------------------------------------------------

@app.command("data")
def clean_data(
    database_url: Optional[str] = typer.Option(
        None, "--db", envvar="DATABASE_URL",
        help="URL de conexión PostgreSQL (o usa DATABASE_URL env var)",
    ),
    tables: Optional[str] = typer.Option(
        None, "--tables", help="Tablas a analizar (separadas por coma)"
    ),
    show_ok: bool = typer.Option(False, "--show-ok"),
) -> None:
    """Analiza calidad de datos en PostgreSQL: duplicados, nulos, FK violations."""
    ui = UI()

    if not database_url:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        ui.error("DATABASE_URL no definida. Usa --db o copia .env.example a .env")
        raise typer.Exit(1)

    table_list = [t.strip() for t in tables.split(",")] if tables else None

    ui.header("Limpieza de datos")
    ui.info(f"  Conectando a: {database_url.split('@')[-1]}")
    ui.newline()

    cleaner = DataCleaner(database_url)
    report = cleaner.scan(table_list)

    if not report.children and not report.issues:
        ui.warning("No se encontraron tablas en la base de datos.")
        return

    tree = Tree(
        f"[bold cyan]database[/bold cyan]  {_score_bar(report.quality_score())}"
    )
    _render_tree(report, tree, show_ok=show_ok)
    console.print(tree)
    _print_summary(report)


# ---------------------------------------------------------------------------
# Comando raíz: corre ambos
# ---------------------------------------------------------------------------

@app.callback(invoke_without_command=True)
def clean(
    ctx: typer.Context,
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="Ruta del proyecto"),
    fix: bool = typer.Option(False, "--fix"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    show_ok: bool = typer.Option(False, "--show-ok"),
    database_url: Optional[str] = typer.Option(
        None, "--db", envvar="DATABASE_URL"
    ),
) -> None:
    """Ejecuta limpieza completa: proyecto + datos."""
    if ctx.invoked_subcommand is not None:
        return

    ctx.invoke(clean_project, path=path, fix=fix, dry_run=dry_run, show_ok=show_ok)

    from dotenv import load_dotenv
    import os
    load_dotenv()
    db = database_url or os.environ.get("DATABASE_URL")
    if db:
        ctx.invoke(clean_data, database_url=db, show_ok=show_ok)
