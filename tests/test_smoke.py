import importlib


def test_import_package():
    pkg = importlib.import_module("four_charm")
    assert pkg is not None
