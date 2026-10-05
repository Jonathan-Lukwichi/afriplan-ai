"""scripts/dev.py: one setup + start command that behaves the same on Windows, macOS and Linux."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("dev", ROOT / "scripts" / "dev.py")
dev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dev)


def test_venv_python_is_scripts_exe_on_windows_and_bin_python_elsewhere(tmp_path):
    assert dev.venv_python(tmp_path, windows=True) == tmp_path / "api" / ".venv" / "Scripts" / "python.exe"
    assert dev.venv_python(tmp_path, windows=False) == tmp_path / "api" / ".venv" / "bin" / "python"


def test_env_file_is_created_from_the_example_once_and_never_overwritten(tmp_path):
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / ".env.example").write_text("ANTHROPIC_API_KEY=\n", encoding="utf-8")
    assert dev.ensure_env_file(tmp_path) is True
    assert (tmp_path / "api" / ".env").read_text(encoding="utf-8") == "ANTHROPIC_API_KEY=\n"

    (tmp_path / "api" / ".env").write_text("ANTHROPIC_API_KEY=sk-mine\n", encoding="utf-8")
    assert dev.ensure_env_file(tmp_path) is False
    assert (tmp_path / "api" / ".env").read_text(encoding="utf-8") == "ANTHROPIC_API_KEY=sk-mine\n"


def test_python_older_than_3_12_is_refused_with_a_reason():
    assert dev.python_problem((3, 11, 9)) is not None
    assert "3.12" in dev.python_problem((3, 11, 9))
    assert dev.python_problem((3, 12, 0)) is None
    assert dev.python_problem((3, 14, 0)) is None


def test_architecture_hook_runs_pytest_with_the_project_venv_when_it_exists(tmp_path):
    hook_spec = importlib.util.spec_from_file_location(
        "check_architecture", ROOT / "scripts" / "hooks" / "check_architecture.py")
    hook = importlib.util.module_from_spec(hook_spec)
    hook_spec.loader.exec_module(hook)

    import sys
    assert hook.pytest_python(tmp_path) == sys.executable          # no venv yet: whatever ran the hook
    venv = dev.venv_python(tmp_path)
    venv.parent.mkdir(parents=True)
    venv.write_bytes(b"")
    assert hook.pytest_python(tmp_path) == str(venv)               # venv has pytest + the app's packages
