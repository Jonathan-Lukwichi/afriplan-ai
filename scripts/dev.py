"""
Set up and run AfriPlan on Windows, macOS or Linux — the same two commands everywhere.

    python scripts/dev.py setup    # once: api/.venv + Python packages, api/.env, npm packages
    python scripts/dev.py start    # backend http://127.0.0.1:8000 + app http://127.0.0.1:5180

(macOS/Linux: type `python3` instead of `python`.) Ctrl+C stops both servers.
Needs Python 3.12+ and Node.js 20+ on PATH; everything else is installed by `setup`.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_PYTHON = (3, 12)
BACKEND_URL = "http://127.0.0.1:8000"
APP_URL = "http://127.0.0.1:5180"


def venv_python(root: Path, windows: bool = os.name == "nt") -> Path:
    """The project's virtual-environment Python (api/.venv), per operating system."""
    venv = root / "api" / ".venv"
    return venv / "Scripts" / "python.exe" if windows else venv / "bin" / "python"


def python_problem(version: tuple) -> str | None:
    """Why this Python cannot run the app, or None when it can."""
    if tuple(version[:2]) >= MIN_PYTHON:
        return None
    need = ".".join(map(str, MIN_PYTHON))
    return (f"Python {need} or newer is needed (this is {version[0]}.{version[1]}). "
            "Install it from https://www.python.org/downloads/ (macOS: `brew install python@3.12`).")


def ensure_env_file(root: Path) -> bool:
    """Create api/.env from api/.env.example if it is missing. True when it was created."""
    env, example = root / "api" / ".env", root / "api" / ".env.example"
    if env.exists():
        return False
    shutil.copyfile(example, env)
    return True


def _npm() -> str:
    npm = shutil.which("npm")   # resolves npm.cmd on Windows
    if npm is None:
        sys.exit("Node.js (npm) not found on PATH. Install Node.js 20+ from https://nodejs.org/")
    return npm


def _run(cmd: list, cwd: Path = ROOT) -> None:
    print("  $", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], cwd=cwd, check=True)


def setup() -> int:
    problem = python_problem(sys.version_info)
    if problem:
        print(problem)
        return 1
    py = venv_python(ROOT)
    print("1/3 Python packages (api/.venv)")
    if not py.exists():
        _run([sys.executable, "-m", "venv", ROOT / "api" / ".venv"])
    _run([py, "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", ROOT / "api" / "requirements.txt"])
    print("2/3 Settings file")
    print("  created api/.env from api/.env.example — add your API keys there (optional)"
          if ensure_env_file(ROOT) else "  api/.env already exists — left unchanged")
    print("3/3 Frontend packages (node_modules)")
    _run([_npm(), "install", "--no-fund", "--no-audit"])
    print(f"\nReady. Start the app with:  {'python' if os.name == 'nt' else 'python3'} scripts/dev.py start")
    return 0


def start() -> int:
    py = venv_python(ROOT)
    if not py.exists() or not (ROOT / "node_modules").exists():
        print("Not set up yet — run:  python scripts/dev.py setup   (macOS/Linux: python3)")
        return 1
    procs = [
        subprocess.Popen([str(py), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
                         cwd=ROOT / "api"),
        subprocess.Popen([_npm(), "run", "dev"], cwd=ROOT),
    ]
    print(f"\n  App:      {APP_URL}\n  API docs: {BACKEND_URL}/docs\n  Ctrl+C stops both.\n", flush=True)
    try:
        while all(p.poll() is None for p in procs):
            try:
                procs[0].wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["setup", "start"])
    return {"setup": setup, "start": start}[ap.parse_args().command]()


if __name__ == "__main__":
    raise SystemExit(main())
