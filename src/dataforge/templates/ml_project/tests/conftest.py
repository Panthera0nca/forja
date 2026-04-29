"""Fixtures compartidos.

Nota: los tests que tocan Postgres asumen una DB disponible en DATABASE_URL.
Para tests unitarios sin DB, usa funciones puras de `transforms/`.
"""
import os

import pytest


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL no definida — skipping tests que tocan Postgres")
    return url
