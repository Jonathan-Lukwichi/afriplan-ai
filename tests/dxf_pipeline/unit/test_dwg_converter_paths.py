"""DWG converters are found where macOS installs them, not only where Windows does."""

from __future__ import annotations

import agent.dxf_pipeline.dwg as dwgmod


def _only_this_path_exists(monkeypatch, path: str) -> None:
    monkeypatch.setattr(dwgmod.shutil, "which", lambda _cand: None)
    monkeypatch.setattr(dwgmod.Path, "exists", lambda self: self.as_posix() == path)


def test_finds_libredwg_from_homebrew_on_apple_silicon(monkeypatch):
    # `brew install libredwg` puts dwg2dxf here; a server launched from the Dock may not
    # have /opt/homebrew/bin on PATH.
    path = "/opt/homebrew/bin/dwg2dxf"
    _only_this_path_exists(monkeypatch, path)
    assert dwgmod.find_dwg2dxf() == path


def test_finds_oda_converter_inside_the_macos_app_bundle(monkeypatch):
    path = "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter"
    _only_this_path_exists(monkeypatch, path)
    assert dwgmod.find_oda_converter() == path
