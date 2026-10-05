"""
DWG → DXF conversion.

`ezdxf` reads DXF, not the proprietary DWG format. Clients usually hand over
DWG, so we convert first. Two converters are supported, tried in order:

  1. LibreDWG `dwg2dxf` — free, GPL, no login, no admin (the default we ship)
  2. ODA File Converter — free but requires an ODA account to download

If neither is present we return a clear, actionable error (never a crash).
Deterministic in spirit: the same DWG always converts to the same DXF. No LLM.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


# LibreDWG dwg2dxf — the default converter (GPL, no login).
_LIBREDWG_CANDIDATES = [
    os.environ.get("LIBREDWG_DWG2DXF", ""),
    "dwg2dxf",
    "dwg2dxf.exe",
    os.path.expanduser(r"~\libredwg\dwg2dxf.exe"),
    os.path.expanduser("~/libredwg/dwg2dxf"),
    r"C:\Program Files\libredwg\dwg2dxf.exe",
    "/opt/homebrew/bin/dwg2dxf",   # macOS `brew install libredwg` (Apple Silicon)
    "/usr/local/bin/dwg2dxf",      # macOS Intel Homebrew / Linux source build
]

# ODA File Converter — fallback (needs an ODA account to install).
_ODA_CANDIDATES = [
    os.environ.get("ODA_CONVERTER", ""),
    "ODAFileConverter",
    "ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
    "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter",
]


@dataclass
class ConversionResult:
    ok: bool
    dxf_bytes: Optional[bytes] = None
    error: str = ""
    converter: str = ""


def _resolve(candidates) -> Optional[str]:
    for cand in candidates:
        if not cand:
            continue
        if os.sep in cand or (os.altsep and os.altsep in cand):
            if Path(cand).exists():
                return cand
        else:
            found = shutil.which(cand)
            if found:
                return found
    return None


def find_dwg2dxf() -> Optional[str]:
    """Locate the LibreDWG dwg2dxf executable, or None."""
    return _resolve(_LIBREDWG_CANDIDATES)


def find_oda_converter() -> Optional[str]:
    """Locate the ODA File Converter executable, or None."""
    return _resolve(_ODA_CANDIDATES)


def is_dwg(file_name: str) -> bool:
    return file_name.lower().strip().endswith(".dwg")


def _convert_via_libredwg(exe: str, dwg_bytes: bytes, file_name: str) -> ConversionResult:
    with tempfile.TemporaryDirectory() as tmp:
        stem = Path(file_name).stem or "input"
        in_dwg = Path(tmp) / f"{stem}.dwg"
        out_dxf = Path(tmp) / f"{stem}.dxf"
        in_dwg.write_bytes(dwg_bytes)
        # dwg2dxf -y -o <out> <in>  (-y = allow ACAD version downgrade)
        proc = subprocess.run(
            [exe, "-y", "-o", str(out_dxf), str(in_dwg)],
            capture_output=True, timeout=180,
        )
        if out_dxf.exists() and out_dxf.stat().st_size > 0:
            return ConversionResult(ok=True, dxf_bytes=out_dxf.read_bytes(), converter=f"libredwg:{exe}")
        return ConversionResult(
            ok=False, converter=f"libredwg:{exe}",
            error=f"dwg2dxf produced no DXF (exit {proc.returncode}). "
                  f"stderr: {proc.stderr.decode('utf-8', 'ignore')[:200]}",
        )


def _convert_via_oda(exe: str, dwg_bytes: bytes, file_name: str) -> ConversionResult:
    with tempfile.TemporaryDirectory() as tmp:
        in_dir = Path(tmp) / "in"
        out_dir = Path(tmp) / "out"
        in_dir.mkdir()
        out_dir.mkdir()
        stem = Path(file_name).stem or "input"
        (in_dir / f"{stem}.dwg").write_bytes(dwg_bytes)
        # ODAFileConverter <in> <out> <ver> <type> <recurse> <audit> [filter]
        proc = subprocess.run(
            [exe, str(in_dir), str(out_dir), "ACAD2018", "DXF", "0", "1", "*.DWG"],
            capture_output=True, timeout=180,
        )
        out = next(iter(out_dir.glob("*.dxf")), None) or next(iter(out_dir.glob("*.DXF")), None)
        if out is not None and out.stat().st_size > 0:
            return ConversionResult(ok=True, dxf_bytes=out.read_bytes(), converter=f"oda:{exe}")
        return ConversionResult(
            ok=False, converter=f"oda:{exe}",
            error=f"ODA converter produced no DXF (exit {proc.returncode}).",
        )


def convert_dwg_to_dxf(dwg_bytes: bytes, file_name: str = "input.dwg") -> ConversionResult:
    """
    Convert DWG bytes to DXF bytes. Tries LibreDWG first, then ODA.
    Returns ConversionResult(ok=False, error=...) if no converter is available
    or conversion fails. Never raises.
    """
    libredwg = find_dwg2dxf()
    oda = find_oda_converter()
    if libredwg is None and oda is None:
        return ConversionResult(
            ok=False,
            error=(
                "No DWG→DXF converter found. Install the free LibreDWG "
                "(https://github.com/LibreDWG/libredwg/releases — no login, unzip "
                "and put dwg2dxf.exe on PATH or in ~/libredwg/; macOS: brew install libredwg), or the ODA File "
                "Converter, or simply 'Save As DXF' from your CAD program and "
                "upload the .dxf directly."
            ),
        )
    try:
        if libredwg is not None:
            res = _convert_via_libredwg(libredwg, dwg_bytes, file_name)
            if res.ok or oda is None:
                return res
        return _convert_via_oda(oda, dwg_bytes, file_name)
    except subprocess.TimeoutExpired:
        return ConversionResult(ok=False, error="DWG→DXF conversion timed out.")
    except Exception as e:  # noqa: BLE001 — conversion must never crash the pipeline
        log.exception("DWG conversion failed")
        return ConversionResult(ok=False, error=f"DWG→DXF conversion failed: {e}")


def ensure_dxf_bytes(file_bytes: bytes, file_name: str) -> ConversionResult:
    """
    Normalise input to DXF bytes. If already DXF, pass through; if DWG, convert.
    """
    if is_dwg(file_name):
        return convert_dwg_to_dxf(file_bytes, file_name)
    return ConversionResult(ok=True, dxf_bytes=file_bytes, converter="none (already DXF)")
