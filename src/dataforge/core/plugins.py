"""Plugin system de forja.

Terceros extienden forja registrando nuevos dominios y arquitecturas via
Python entry points:

    [project.entry-points."forja.plugins"]
    mi_plugin = "mi_paquete.plugin:register"

La función `register(registry: PluginRegistry)` recibe el registro global
y añade dominios/arquitecturas. forja la llama automáticamente al arrancar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PluginDomain:
    key: str
    display_name: str
    description: str
    architecture: str
    keywords: list[str]
    suggested_entities: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    notes: str = ""
    source: str = ""          # nombre del plugin que lo registró


@dataclass
class PluginArchitecture:
    key: str
    description: str
    template_path: Path
    source: str = ""


class PluginRegistry:
    """Registro central de extensiones de forja."""

    def __init__(self) -> None:
        self._domains: dict[str, PluginDomain] = {}
        self._architectures: dict[str, PluginArchitecture] = {}
        self._sources: list[str] = []

    def add_domain(
        self,
        key: str,
        display_name: str,
        description: str,
        architecture: str,
        keywords: list[str],
        suggested_entities: list[str] | None = None,
        features: list[str] | None = None,
        notes: str = "",
        _source: str = "",
    ) -> None:
        self._domains[key] = PluginDomain(
            key=key,
            display_name=display_name,
            description=description,
            architecture=architecture,
            keywords=keywords,
            suggested_entities=suggested_entities or [],
            features=features or [],
            notes=notes,
            source=_source,
        )

    def add_architecture(
        self,
        key: str,
        description: str,
        template_path: Path,
        _source: str = "",
    ) -> None:
        self._architectures[key] = PluginArchitecture(
            key=key,
            description=description,
            template_path=template_path,
            source=_source,
        )

    @property
    def domains(self) -> dict[str, PluginDomain]:
        return dict(self._domains)

    @property
    def architectures(self) -> dict[str, PluginArchitecture]:
        return dict(self._architectures)

    @property
    def sources(self) -> list[str]:
        return list(self._sources)

    def _add_source(self, name: str) -> None:
        if name not in self._sources:
            self._sources.append(name)


_registry: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    """Retorna el registro global, cargando plugins si es la primera vez."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
        _load_plugins(_registry)
    return _registry


def _load_plugins(registry: PluginRegistry) -> None:
    """Descubre y carga plugins via entry points."""
    try:
        from importlib.metadata import entry_points
        eps = entry_points(group="forja.plugins")
    except Exception:
        return

    for ep in eps:
        try:
            fn = ep.load()
            fn(registry)
            registry._add_source(ep.name)
        except Exception as exc:
            import warnings
            warnings.warn(f"Plugin '{ep.name}' falló al cargar: {exc}", stacklevel=2)
