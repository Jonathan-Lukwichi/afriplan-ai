"""scripts/hooks/skill_feedback_reminder.py: after a scored run, remind Claude to feed the result back into the BoQ skills."""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("skill_feedback_reminder", ROOT / "scripts" / "hooks" / "skill_feedback_reminder.py")
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


def _payload(tool: str, command: str) -> dict:
    return {"tool_name": tool, "tool_input": {"command": command}}


def test_a_doe_finish_run_in_any_shell_triggers_the_reminder():
    for tool, cmd in [
        ("Bash", 'api/.venv/bin/python doe/execution/project.py finish "/p/x" --reference wedela'),
        ("PowerShell", r'api\.venv\Scripts\python.exe doe\execution\project.py finish "C:\p\x"'),
    ]:
        msg = hook.reminder(_payload(tool, cmd))
        assert msg and "improving-boq-skills" in msg


def test_an_evaluate_run_triggers_the_reminder():
    assert hook.reminder(_payload("Bash", "api/.venv/bin/python scripts/evaluate.py --project wedela --pipeline dxf"))


def test_a_command_that_only_mentions_the_scripts_stays_quiet():
    msg = "git commit -m 'hook runs after every scored run (project.py finish, scripts/evaluate.py)'"
    assert hook.reminder(_payload("PowerShell", msg)) is None
    assert hook.reminder(_payload("Bash", "grep -n 'project.py finish' doe/playbook/PLAYBOOK.md")) is None


def test_the_venv_variable_form_still_triggers():
    assert hook.reminder(_payload("Bash", '$PY doe/execution/project.py finish "/p/x"'))


def test_other_commands_and_tools_stay_quiet():
    assert hook.reminder(_payload("Bash", "api/.venv/bin/python doe/execution/project.py prepare /p/x")) is None
    assert hook.reminder(_payload("Bash", "git status")) is None
    assert hook.reminder({"tool_name": "Edit", "tool_input": {"file_path": "doe/execution/project.py"}}) is None


def test_main_emits_post_tool_use_context_json_and_never_blocks(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_payload("Bash", "python doe/execution/project.py finish x"))))
    assert hook.main() == 0
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "improving-boq-skills" in out["hookSpecificOutput"]["additionalContext"]


def test_main_is_silent_on_a_malformed_payload(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert hook.main() == 0
    assert capsys.readouterr().out == ""
