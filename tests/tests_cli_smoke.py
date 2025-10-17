# finops-platform/tests/test_cli_smoke.py
import runpy


def test_cli_module_loads():
    mod = runpy.run_path("cli.py")
    assert "main" in mod
