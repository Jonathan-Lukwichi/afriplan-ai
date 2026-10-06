"""Load test: N users upload a drawing set at the same moment and follow their run to the end.

    $PY scripts/load_test.py --users 10 --files "data/projects/wedela/raw/Wedela Electrical" --start-server

With --start-server it starts its own API server (uvicorn, a throw-away SQLite file, port 8011),
so the server's memory can be sampled; without it, it targets --base and reports no memory.
Per user it records: refused (busy) or accepted, seconds waiting in line, seconds to finish,
final status. Uses only the standard library and httpx (already in the venv).
"""

from __future__ import annotations

import argparse
import os
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


# ── server memory (no extra dependency) ──
def rss_mb(pid: int) -> float | None:
    """Resident memory of one process in MB (Windows working set, Linux VmRSS)."""
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class PMC(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
            h = ctypes.windll.kernel32.OpenProcess(0x1000 | 0x0010, False, pid)
            if not h:
                return None
            try:
                pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
                if not ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
                    return None
                return pmc.WorkingSetSize / 2**20
            finally:
                ctypes.windll.kernel32.CloseHandle(h)
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    except OSError:
        return None
    return None


def real_pid(proc: subprocess.Popen) -> int:
    """On Windows a venv's python.exe is a launcher that starts the real interpreter as a
    child process — the server's memory is in that child, so measure it, not the launcher."""
    if os.name != "nt":
        return proc.pid
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          f"(Get-CimInstance Win32_Process -Filter 'ParentProcessId={proc.pid}').ProcessId"],
                         capture_output=True, text=True).stdout.split()
    return int(out[0]) if out else proc.pid


def summarise(rows: list[dict], peak_mb: float | None) -> dict:
    done = [r for r in rows if r["status"] in ("passed", "failed")]
    waits = [r["wait_s"] for r in done if r.get("wait_s") is not None]
    totals = [r["total_s"] for r in done if r.get("total_s") is not None]
    return {
        "users": len(rows),
        "refused_busy": sum(r["status"] == "busy" for r in rows),
        "passed": sum(r["status"] == "passed" for r in rows),
        "failed": sum(r["status"] == "failed" for r in rows),
        "errors": sum(r["status"] == "error" for r in rows),
        "wait_s_max": round(max(waits), 1) if waits else None,
        "wait_s_median": round(statistics.median(waits), 1) if waits else None,
        "total_s_max": round(max(totals), 1) if totals else None,
        "total_s_median": round(statistics.median(totals), 1) if totals else None,
        "server_peak_mb": round(peak_mb) if peak_mb else None,
    }


# ── one simulated user ──
def one_user(i: int, base: str, files: list[Path], pipeline: str, go: threading.Event, out: list) -> None:
    row = {"user": i + 1, "status": "error"}
    try:
        payload = [("files", (f.name, f.read_bytes(), "application/octet-stream")) for f in files]
        with httpx.Client(base_url=base, timeout=httpx.Timeout(600, connect=30)) as c:
            go.wait()                                         # everyone presses Run together
            t0 = time.monotonic()
            r = c.post("/api/runs", data={"pipeline": pipeline}, files=payload)
            if r.status_code == 503:
                row.update(status="busy", detail=r.json().get("detail"))
                return
            r.raise_for_status()
            rid, started = r.json()["run_id"], None
            while True:
                time.sleep(2)
                body = c.get(f"/api/runs/{rid}").json()
                waiting = (body.get("progress") or {}).get("stage") == "queued"
                if started is None and not waiting:
                    started = time.monotonic()
                if body["status"] != "running":
                    end = time.monotonic()
                    row.update(status=body["status"], run_id=rid, error=body.get("error"),
                               wait_s=(started or end) - t0, total_s=end - t0)
                    return
    except Exception as e:  # noqa: BLE001 — a load test reports every failure, it never stops
        row["detail"] = repr(e)
    finally:
        out.append(row)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=10)
    ap.add_argument("--files", required=True, help="a folder of .dwg/.dxf/.pdf files, or one file")
    ap.add_argument("--pipeline", default="dxf", choices=["dxf", "pdf"])
    ap.add_argument("--base", default="http://127.0.0.1:8011")
    ap.add_argument("--start-server", action="store_true")
    a = ap.parse_args()

    src = Path(a.files)
    exts = {".dwg", ".dxf"} if a.pipeline == "dxf" else {".pdf"}
    files = sorted(p for p in (src.iterdir() if src.is_dir() else [src]) if p.suffix.lower() in exts)
    if not files:
        print("no input files found"); return 2

    server = None
    if a.start_server:
        db = Path(tempfile.mkdtemp()) / "load.db"
        env = {**os.environ, "DATABASE_URL": f"sqlite:///{db.as_posix()}"}
        port = a.base.rsplit(":", 1)[1]
        server = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", port],
                                  cwd=ROOT / "api", env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(120):
            try:
                if httpx.get(a.base + "/api/health", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(1)
        else:
            server.kill(); print("server did not start"); return 2

    pid = real_pid(server) if server else None
    peak = [rss_mb(pid) if pid else None]
    if pid:
        print(f"server pid {pid}, idle {peak[0]:.0f} MB")
    stop = threading.Event()

    def sample():
        while not stop.is_set():
            m = rss_mb(pid)
            if m and (peak[0] is None or m > peak[0]):
                peak[0] = m
            time.sleep(0.25)

    sampler = threading.Thread(target=sample, daemon=True)
    if server:
        sampler.start()

    print(f"{a.users} users × {len(files)} files ({sum(f.stat().st_size for f in files) / 2**20:.1f} MB each), "
          f"pipeline {a.pipeline}, server {a.base}")
    rows: list[dict] = []
    go = threading.Event()
    users = [threading.Thread(target=one_user, args=(i, a.base, files, a.pipeline, go, rows)) for i in range(a.users)]
    for u in users:
        u.start()
    time.sleep(1)
    t0 = time.monotonic()
    go.set()
    for u in users:
        u.join()
    stop.set()
    if server:
        if pid != server.pid:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        server.terminate()

    for r in sorted(rows, key=lambda r: r["user"]):
        print(f"  user {r['user']:2}: {r['status']:7} wait {r.get('wait_s', 0):6.1f} s  total {r.get('total_s', 0):6.1f} s"
              + (f"  {r.get('error') or r.get('detail')}" if r["status"] not in ("passed",) else ""))
    s = summarise(rows, peak[0])
    print("SUMMARY", s, f"wall {time.monotonic() - t0:.0f} s")
    return 0 if s["errors"] == 0 and s["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
