"""Test de humo: el package importa y tiene versión."""
import miproyecto


def test_package_imports():
    assert hasattr(miproyecto, "__version__")
    assert isinstance(miproyecto.__version__, str)
