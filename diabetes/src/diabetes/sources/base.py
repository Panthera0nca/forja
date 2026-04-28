"""Protocolo que define cómo se ve un Source."""
from __future__ import annotations

from typing import Iterable, Protocol, TypeVar

T = TypeVar("T", covariant=True)


class Source(Protocol[T]):
    """Un Source sabe traer datos crudos de un origen externo.

    No valida, no transforma, no persiste. Solo trae.
    """

    name: str

    def fetch(self) -> Iterable[T]:
        """Retorna un iterable de items crudos."""
        ...
