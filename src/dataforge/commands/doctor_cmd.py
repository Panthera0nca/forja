"""`dfg doctor` — diagnóstico del estado de salud del proyecto."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from dataforge.core.project import detect_project
from dataforge.core.ui import UI

console = Console()

_OK   = "[bold green]✓[/]"
_WARN = "[bold yellow]⚠[/]"
_FAIL = "[bold red]✗[/]"


def _check(label: str, ok: bool, warn: bool = False, detail: str = "") -> tuple[str, str, str]:
    icon = _OK if ok else (_WARN if warn else _FAIL)
    status = "[green]ok[/]" if ok else ("[yellow]aviso[/]" if warn else "[red]error[/]")
    return icon, label, f"{status}{'  ' + detail if detail else ''}"


def _has_not_implemented(path: Path) -> bool:
    try:
        return "raise NotImplementedError" in path.read_text()
    except Exception:
        return False


def _scan_layer(layer_dir: Path, skip: set[str]) -> tuple[int, int]:
    """Retorna (total, pendientes) de archivos con NotImplementedError."""
    if not layer_dir.is_dir():
        return 0, 0
    files = [f for f in layer_dir.glob("*.py") if f.stem not in skip]
    pending = sum(1 for f in files if _has_not_implemented(f))
    return len(files), pending


def doctor(
    fix: bool = typer.Option(False, "--fix", help="(reservado para versiones futuras)"),
) -> None:
    ui = UI()
    info = detect_project()
    if info is None:
        ui.error("No estás dentro de un proyecto DataForge.")
        raise typer.Exit(1)

    root = Path(info["root"])
    package = info["package"]
    src = root / "src" / package
    arch = info.get("type", "etl")

    ui.header(f"doctor · {info['name']}  [{arch}]")

    checks: list[tuple[str, str, str]] = []

    # ------------------------------------------------------------------
    # Entorno
    # ------------------------------------------------------------------
    has_env     = (root / ".env").exists()
    has_docker  = (root / "docker-compose.yml").exists()
    has_tests   = (root / "tests").is_dir() and any((root / "tests").glob("test_*.py"))

    checks.append(_check(".env presente",          has_env,    warn=not has_env,
                          detail="" if has_env else "copiá .env.example a .env"))
    checks.append(_check("docker-compose.yml",     has_docker, warn=not has_docker))
    checks.append(_check("tests/test_*.py existe", has_tests,  warn=not has_tests,
                          detail="" if has_tests else "no hay tests en tests/"))

    # ------------------------------------------------------------------
    # Migraciones
    # ------------------------------------------------------------------
    migrations_dir = root / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql")) if migrations_dir.is_dir() else []
    has_migrations = len(sql_files) > 0
    checks.append(_check(
        f"migraciones ({len(sql_files)} archivos)",
        has_migrations,
        warn=not has_migrations,
        detail="creá una con dfg add entity" if not has_migrations else
               "corré dfg migrate --dry-run para ver pendientes",
    ))

    # ------------------------------------------------------------------
    # Capas: sources, pipelines, exporters
    # ------------------------------------------------------------------
    skip_base = {"__init__", "base"}

    for layer, friendly in [
        ("sources",   "sources"),
        ("pipelines", "pipelines"),
        ("exporters", "exporters"),
    ]:
        total, pending = _scan_layer(src / layer, skip_base)
        if total == 0:
            checks.append(_check(f"{friendly} (ninguno)", False, warn=True,
                                  detail=f"dfg add {layer[:-1]} <nombre>"))
        elif pending == 0:
            checks.append(_check(f"{friendly} ({total} implementados)", True))
        else:
            implemented = total - pending
            checks.append(_check(
                f"{friendly} ({implemented}/{total} implementados)",
                ok=False, warn=True,
                detail=f"{pending} con NotImplementedError pendiente",
            ))

    # ------------------------------------------------------------------
    # Package importable
    # ------------------------------------------------------------------
    import sys
    src_str = str(root / "src")
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
    try:
        import importlib
        importlib.import_module(package)
        importable = True
    except Exception as exc:
        importable = False
        import_error = str(exc)

    checks.append(_check(
        f"package '{package}' importable",
        importable,
        detail="" if importable else import_error,
    ))

    # ------------------------------------------------------------------
    # Tabla de resultados
    # ------------------------------------------------------------------
    console.print()
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column("icon",   justify="center", no_wrap=True)
    t.add_column("check",  style="bold")
    t.add_column("status", justify="left")

    errors = warns = oks = 0
    for icon, label, status in checks:
        t.add_row(icon, label, status)
        if "error" in status:
            errors += 1
        elif "aviso" in status:
            warns += 1
        else:
            oks += 1

    console.print(t)
    console.print()

    if errors:
        ui.error(f"{errors} error(s)  ·  {warns} aviso(s)  ·  {oks} ok")
        raise typer.Exit(1)
    elif warns:
        ui.warning(f"{warns} aviso(s)  ·  {oks} ok — proyecto funcional con observaciones")
    else:
        ui.success(f"Todo en orden — {oks} checks pasados")
