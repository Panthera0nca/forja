"""Exporter Protocol: contrato mínimo para exportar datos a archivos portables."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Protocol


class Exporter(Protocol):
    """Un Exporter toma registros y los escribe a un archivo externo.

    No consulta la DB directamente — recibe los datos ya procesados.
    """

    name: str

    def export(self, records: Iterable[Any], dest: Path) -> Path:
        """Escribe los registros en `dest` y retorna la ruta del archivo creado."""
        ...
