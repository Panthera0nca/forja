"""Renderer de templates: copia + sustitución Jinja2.

Convenciones:
- Archivos `.j2` → se renderizan con Jinja2, se guarda sin el sufijo.
- Archivos normales → se copian tal cual.
- Rutas con `{{package_name}}` → se sustituye en el path antes de crear el directorio.
- Archivos `_dotfile_X` → se renombra a `.X` al salir (evita problemas de empaquetado).
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

from jinja2 import Environment, FileSystemLoader, StrictUndefined


TEMPLATES_ROOT = Path(__file__).parent.parent / "templates"


def _render_path(path_part: str, context: dict) -> str:
    """Sustituye {{vars}} en una porción de path y normaliza _dotfile_."""
    for key, value in context.items():
        path_part = path_part.replace("{{" + key + "}}", str(value))
    if path_part.startswith("_dotfile_"):
        path_part = "." + path_part[len("_dotfile_"):]
    return path_part


def _translate_path(relative: Path, context: dict) -> Path:
    """Traduce una ruta relativa del template a la ruta de destino."""
    parts = [_render_path(p, context) for p in relative.parts]
    final = Path(*parts) if parts else Path()
    # Remover sufijo .j2 si lo tiene
    if final.suffix == ".j2":
        final = final.with_suffix("")
    return final


def iter_template_files(template: str) -> Iterable[Path]:
    """Itera sobre los archivos de un template (rutas relativas al template root)."""
    template_dir = TEMPLATES_ROOT / template
    if not template_dir.is_dir():
        raise FileNotFoundError(f"Template '{template}' no encontrado en {TEMPLATES_ROOT}")
    for path in sorted(template_dir.rglob("*")):
        if path.is_file():
            yield path.relative_to(template_dir)


def render_template(template: str, destination: Path, context: dict) -> list[Path]:
    """Renderiza un template completo en `destination`. Retorna lista de archivos creados."""
    template_dir = TEMPLATES_ROOT / template
    if not template_dir.is_dir():
        raise FileNotFoundError(f"Template '{template}' no encontrado en {TEMPLATES_ROOT}")

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )

    created: list[Path] = []
    for rel in iter_template_files(template):
        dest_rel = _translate_path(rel, context)
        dest_abs = destination / dest_rel
        dest_abs.parent.mkdir(parents=True, exist_ok=True)

        if rel.suffix == ".j2":
            # Renderizar con Jinja2
            template_obj = env.get_template(str(rel).replace("\\", "/"))
            dest_abs.write_text(template_obj.render(**context))
        else:
            # Copia binaria-segura
            shutil.copyfile(template_dir / rel, dest_abs)

        created.append(dest_abs)

    return created


def render_template_from_path(template_dir: Path, destination: Path, context: dict) -> list[Path]:
    """Igual que render_template pero recibe una ruta absoluta (para plugins)."""
    if not template_dir.is_dir():
        raise FileNotFoundError(f"Template dir '{template_dir}' no encontrado")

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )

    created: list[Path] = []
    for path in sorted(template_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(template_dir)
        dest_rel = _translate_path(rel, context)
        dest_abs = destination / dest_rel
        dest_abs.parent.mkdir(parents=True, exist_ok=True)

        if rel.suffix == ".j2":
            template_obj = env.get_template(str(rel).replace("\\", "/"))
            dest_abs.write_text(template_obj.render(**context))
        else:
            shutil.copyfile(template_dir / rel, dest_abs)

        created.append(dest_abs)

    return created


def render_file(template_rel_path: str, destination: Path, context: dict) -> Path:
    """Renderiza un solo archivo .j2 (relativo a TEMPLATES_ROOT) en `destination`.

    Pensado para generación de componentes (`add entity`, `add source`, etc.),
    donde cada archivo va a una ruta distinta del proyecto.
    """
    template_path = TEMPLATES_ROOT / template_rel_path
    if not template_path.is_file():
        raise FileNotFoundError(f"Template '{template_rel_path}' no encontrado")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_ROOT)),
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )
    template_obj = env.get_template(template_rel_path.replace("\\", "/"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(template_obj.render(**context))
    return destination
