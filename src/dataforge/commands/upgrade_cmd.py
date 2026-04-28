"""`dfg upgrade` — actualizar un proyecto generado con una versión anterior de forja."""
from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import typer

from dataforge import __version__ as CURRENT_VERSION
from dataforge.core.project import detect_project
from dataforge.core.templates import TEMPLATES_ROOT, render_file
from dataforge.core.ui import UI


class _Addition(NamedTuple):
    description: str
    archs: list[str]          # arquitecturas donde aplica ("*" = todas)
    check: str                # ruta relativa al root que indica si ya está presente
    template: str             # ruta relativa a TEMPLATES_ROOT
    dest: str                 # ruta relativa al root (con {package} expandible)


# Registro de adiciones por versión.
# Cada entrada describe un archivo que se agregó en esa versión.
UPGRADES: dict[str, list[_Addition]] = {
    "0.5.0": [
        _Addition(
            description="GitHub Actions CI (.github/workflows/ci.yml)",
            archs=["*"],
            check=".github/workflows/ci.yml",
            template="{arch}_project/_dotfile_github/workflows/ci.yml.j2",
            dest=".github/workflows/ci.yml",
        ),
        _Addition(
            description="Capa exporters (base.py)",
            archs=["etl", "ml"],
            check="src/{package}/exporters/base.py",
            template="{arch}_project/src/{{package_name}}/exporters/base.py",
            dest="src/{package}/exporters/base.py",
        ),
        _Addition(
            description="Capa exporters (__init__.py)",
            archs=["etl", "ml"],
            check="src/{package}/exporters/__init__.py",
            template="{arch}_project/src/{{package_name}}/exporters/__init__.py.j2",
            dest="src/{package}/exporters/__init__.py",
        ),
    ],
}

VERSION_ORDER = ["0.1.0", "0.5.0"]


def _versions_to_apply(from_version: str) -> list[str]:
    """Retorna versiones pendientes en orden."""
    try:
        start = VERSION_ORDER.index(from_version)
    except ValueError:
        start = 0
    return VERSION_ORDER[start + 1:]


def _expand(path: str, package: str, arch: str) -> str:
    return path.replace("{package}", package).replace("{arch}", arch)


def upgrade(
    dry_run: bool = typer.Option(False, "--dry-run", help="Mostrar qué se agregaría sin aplicar"),
) -> None:
    ui = UI()
    info = detect_project()
    if info is None:
        ui.error("No estás dentro de un proyecto DataForge.")
        raise typer.Exit(1)

    root = Path(info["root"])
    package = info["package"]
    arch = info.get("type", "etl")

    # Leer forja_version del manifest
    manifest_path = root / "dataforge.toml"
    manifest_text = manifest_path.read_text()

    import re
    m = re.search(r'forja_version\s*=\s*"([^"]+)"', manifest_text)
    project_forja_version = m.group(1) if m else "0.1.0"

    ui.header(f"upgrade · {info['name']}")
    ui.key_value("Versión actual del proyecto", project_forja_version)
    ui.key_value("Versión de forja instalada",  CURRENT_VERSION)
    ui.newline()

    if project_forja_version == CURRENT_VERSION:
        ui.success("El proyecto ya está en la versión más reciente.")
        raise typer.Exit(0)

    pending_versions = _versions_to_apply(project_forja_version)
    if not pending_versions:
        ui.success("El proyecto ya está al día.")
        raise typer.Exit(0)

    # Recopilar adiciones pendientes
    to_add: list[tuple[str, _Addition]] = []
    for version in pending_versions:
        for addition in UPGRADES.get(version, []):
            applies = addition.archs == ["*"] or arch in addition.archs
            if not applies:
                continue
            check_path = root / _expand(addition.check, package, arch)
            if check_path.exists():
                continue
            to_add.append((version, addition))

    if not to_add:
        ui.success(f"Nada que agregar — el proyecto ya tiene todo lo de v{CURRENT_VERSION}.")
        _update_forja_version(manifest_path, manifest_text, CURRENT_VERSION, dry_run, ui)
        raise typer.Exit(0)

    ui.info(f"{len(to_add)} archivo(s) para agregar:")
    ui.newline()

    from dataforge import __version__ as _fv
    context = {
        "project_name":   info["name"],
        "package_name":   package,
        "category":       info.get("category", "generic"),
        "domain":         info.get("domain", "generic"),
        "python_version": "3.12",
        "postgres_image": "postgres:16-alpine",
        "forja_version":  _fv,
    }

    for version, addition in to_add:
        dest_rel = _expand(addition.dest, package, arch)
        dest_abs = root / dest_rel
        tpl = _expand(addition.template, package, arch)

        if dry_run:
            ui.info(f"[v{version}] + {dest_rel}  ({addition.description})")
            continue

        try:
            # Archivos sin .j2 → copiar directamente
            tpl_abs = TEMPLATES_ROOT / tpl
            if tpl_abs.exists() and tpl_abs.suffix != ".j2":
                dest_abs.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copyfile(tpl_abs, dest_abs)
            else:
                render_file(tpl, dest_abs, context)
            ui.file_created(dest_rel)
        except Exception as exc:
            ui.warning(f"No se pudo agregar '{dest_rel}': {exc}")

    if not dry_run:
        _update_forja_version(manifest_path, manifest_text, CURRENT_VERSION, dry_run, ui)
        ui.newline()
        ui.success(f"Proyecto actualizado a forja v{CURRENT_VERSION}")
    else:
        ui.newline()
        ui.warning("Modo dry-run — no se aplicó nada.")


def _update_forja_version(
    manifest_path: Path,
    manifest_text: str,
    new_version: str,
    dry_run: bool,
    ui: UI,
) -> None:
    import re
    if dry_run:
        return
    if re.search(r'forja_version\s*=', manifest_text):
        updated = re.sub(
            r'forja_version\s*=\s*"[^"]+"',
            f'forja_version = "{new_version}"',
            manifest_text,
        )
    else:
        updated = manifest_text.rstrip() + f'\nforja_version = "{new_version}"\n'
    manifest_path.write_text(updated)
    ui.file_modified("dataforge.toml")
