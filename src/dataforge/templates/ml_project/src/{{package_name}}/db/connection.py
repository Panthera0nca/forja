"""Pool de conexiones Postgres con psycopg3.

Un solo pool por proceso. Se crea perezosamente la primera vez que se pide.
Los repositorios piden conexiones vía `get_connection()` (context manager).
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from dotenv import load_dotenv
from psycopg import Connection
from psycopg_pool import ConnectionPool


load_dotenv()


_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    """Retorna el pool global, creándolo si no existe."""
    global _pool
    if _pool is None:
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError(
                "DATABASE_URL no está definida. Copia .env.example a .env."
            )
        _pool = ConnectionPool(conninfo=url, min_size=1, max_size=10, open=True)
    return _pool


@contextmanager
def get_connection() -> Iterator[Connection]:
    """Context manager que saca una conexión del pool y la devuelve al salir."""
    pool = get_pool()
    with pool.connection() as conn:
        yield conn


def close_pool() -> None:
    """Cerrar el pool (útil en tests o al terminar procesos largos)."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
