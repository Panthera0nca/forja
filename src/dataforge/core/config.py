"""Configuración global del CLI y manifest por proyecto.

Dos niveles:
- Global: ~/.config/dataforge/config.json (defaults del usuario)
- Proyecto: <proyecto>/dataforge.toml (metadata del proyecto generado)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ----------------------------- Config global del CLI -----------------------------


class DataForgeConfig(BaseSettings):
    """Preferencias globales del usuario. Se sobreescriben con DATAFORGE_* env vars."""

    model_config = SettingsConfigDict(env_prefix="DATAFORGE_", env_file=".env")

    home: Path = Field(default_factory=lambda: Path.home() / ".config" / "dataforge")
    default_python: str = "3.12"
    default_postgres_image: str = "postgres:16-alpine"
    editor: str = "vim"

    @classmethod
    def load(cls) -> "DataForgeConfig":
        config_path = Path.home() / ".config" / "dataforge" / "config.json"
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text())
                return cls(**data)
            except (json.JSONDecodeError, ValueError):
                pass
        return cls()

    def save(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        config_path = self.home / "config.json"
        config_path.write_text(json.dumps(self.model_dump(mode="json"), indent=2, default=str))


def get_config() -> DataForgeConfig:
    return DataForgeConfig.load()


# ----------------------------- Manifest por proyecto -----------------------------


class ProjectManifest(BaseModel):
    """Lo que vive en `dataforge.toml` de cada proyecto generado."""

    name: str
    package: str
    type: str = "etl"
    version: str = "0.1.0"
    sources: list[str] = Field(default_factory=list)
    pipelines: list[str] = Field(default_factory=list)

    @classmethod
    def load(cls, root: Path) -> Optional["ProjectManifest"]:
        manifest_path = root / "dataforge.toml"
        if not manifest_path.exists():
            return None
        try:
            data = tomllib.loads(manifest_path.read_text())
        except tomllib.TOMLDecodeError:
            return None
        return cls(**data.get("project", {}))
