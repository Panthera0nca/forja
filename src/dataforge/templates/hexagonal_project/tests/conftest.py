import os
import pytest


@pytest.fixture(scope="session")
def db_url():
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL no definida — tests de integración omitidos")
    return url
