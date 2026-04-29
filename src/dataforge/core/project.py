"""Detección de proyectos DataForge en el directorio actual."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from dataforge.core.config import ProjectManifest


def find_project_root(start: Optional[Path] = None) -> Optional[Path]:
    """Sube por el árbol buscando un dataforge.toml."""
    current = (start or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        if (parent / "dataforge.toml").exists():
            return parent
    return None


def detect_project(start: Optional[Path] = None) -> Optional[dict]:
    """Retorna info del proyecto DataForge o None si no está dentro de uno."""
    root = find_project_root(start)
    if root is None:
        return None

    manifest = ProjectManifest.load(root)
    if manifest is None:
        return None

    # domain: usa el campo explícito si existe, si no cae a category
    domain = manifest.domain or manifest.category or "generic"

    return {
        "root": root,
        "name": manifest.name,
        "package": manifest.package,
        "type": manifest.type,
        "category": manifest.category,
        "domain": domain,
        "sources_count": len(manifest.sources),
        "pipelines_count": len(manifest.pipelines),
        "has_migrations": (root / "migrations").is_dir(),
        "has_docker": (root / "docker-compose.yml").exists(),
    }
