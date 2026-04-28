"""Test de humo: el package importa y tiene versión."""
import diabetes


def test_package_imports():
    assert hasattr(diabetes, "__version__")
    assert isinstance(diabetes.__version__, str)
