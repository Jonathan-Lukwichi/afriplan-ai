# AfriPlan Electrical

A South African electrical **Bill of Quantities (BoQ)** estimator for contractors and tender
preparation. Give it a drawing set — PDF, DWG/DXF CAD files, or both — and get a priced,
SANS 10142-1-checked BoQ as Excel and PDF.

There are two ways to use it:

| | **Web app** | **DOE workflow** (VS Code + Claude Code) |
|---|---|---|
| For | contractors, demos | your own estimating |
| How | upload drawings in the browser | point Claude Code at a project folder |
| PDF reading | Claude API key or free Gemini key | your Claude subscription (no API bill) |
| Output | BoQ on screen + Excel/PDF export | Excel + PDF in `<folder>/AfriPlan_Output` |

Works on **Windows, macOS and Linux**. See [`CLAUDE.md`](CLAUDE.md) for the architecture rules
and [`docs/architecture.md`](docs/architecture.md) for the whole system on one page.

---

## 1. Install the prerequisites (once per computer)

| Tool | Version | Windows | macOS |
|---|---|---|---|
| **Git** | any | https://git-scm.com/download/win | `xcode-select --install` |
| **Python** | **3.12 or newer** | https://www.python.org/downloads/ (tick *Add python.exe to PATH*) | `brew install python@3.12` |
| **Node.js** | **20 or newer** | https://nodejs.org/ (LTS) | `brew install node` |
| LibreDWG *(optional — DWG uploads)* | 0.14 | [releases](https://github.com/LibreDWG/libredwg/releases): unzip, put `dwg2dxf.exe` on PATH or in `%USERPROFILE%\libredwg\` | `brew install libredwg` |
| Claude Code *(optional — DOE workflow)* | latest | https://claude.com/claude-code | same |

Without LibreDWG, DXF files still work — only `.dwg` needs converting (or *Save As DXF* in your CAD program).
macOS without Homebrew: install it from https://brew.sh first.

## 2. Get the code and set it up (once)

```bash
git clone https://github.com/Jonathan-Lukwichi/afriplan-ai.git
cd afriplan-ai
python scripts/dev.py setup        # macOS/Linux: python3 scripts/dev.py setup
```

`setup` creates the Python environment in `api/.venv`, installs the Python and npm packages,
and creates `api/.env` from `api/.env.example`.

**API keys (optional).** Open `api/.env` and add `ANTHROPIC_API_KEY` (paid, best) or
`GEMINI_API_KEY` (free, from https://aistudio.google.com/apikey) to let the **web app** read
PDF drawings. Without a key, DWG/DXF estimating, auditing and exports all still work.
The DOE workflow needs no key. `api/.env` is never committed.

**Windows tip:** clone into a short path (e.g. `C:\dev\afriplan-ai`). Very deep folders can
exceed Windows' 260-character path limit while installing packages.

## 3. Run the web app

```bash
python scripts/dev.py start        # macOS/Linux: python3 scripts/dev.py start
```

Open **http://127.0.0.1:5180** → *Sign in* (demo login, pre-filled). API docs: http://127.0.0.1:8000/docs.
`Ctrl+C` stops both servers.

<details><summary>Or start the two servers by hand (two terminals)</summary>

```powershell
# Windows (PowerShell)
cd api; .venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
npm run dev
```
```bash
# macOS / Linux
cd api && .venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
npm run dev
```
</details>

## 4. Run the DOE workflow (Claude Code)

Open this folder in VS Code with the Claude Code extension (or run `claude` in a terminal here)
and say, for example: *"estimate the project in `<path to the drawings folder>`"*.
Claude Code runs the `estimate-project` skill: Python prepares every page, Claude reads them on
your subscription, Python checks, combines and prices them. The Excel + PDF BoQ lands in
`<folder>/AfriPlan_Output`. The steps it runs ([`doe/execution/project.py`](doe/execution/project.py)):

```bash
# Windows: api\.venv\Scripts\python.exe   macOS/Linux: api/.venv/bin/python
<python> doe/execution/project.py prepare "<project folder>"
<python> doe/execution/project.py finish  "<project folder>"
```

## 5. Check everything works

```bash
# Windows: api\.venv\Scripts\python.exe   macOS/Linux: api/.venv/bin/python
<python> -m pytest -q -p no:warnings       # ~530 tests, no network, ~2 min
npm run build
```

A fresh clone passes with a few tests **skipped**: those need the Wedela reference drawings and
bill, which are client data and never in this public repo (`data/projects/*/raw/`, see
[ADR-0005](docs/adr/)). To use your own reference project, see
[`.claude/skills/add-reference-project/`](.claude/skills/add-reference-project/SKILL.md).

## Deploy

One Docker image serves the API and the built app — see [`docs/deploy-render.md`](docs/deploy-render.md).
