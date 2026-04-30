"""
ContractorProfile persistence.

Saves the contractor's company info, markup/contingency/VAT defaults,
and labour rates to a local JSON file so they don't have to re-enter
them on every visit. Lives in ~/.afriplan/profile.json by default.

Failure-tolerant: every disk error is logged and falls back to a
default profile. We never let a corrupted profile file kill the app.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from agent.shared.project import ContractorProfile

log = logging.getLogger(__name__)


def default_profile_path() -> Path:
    """Resolve the default profile path; respects AFRIPLAN_PROFILE env override."""
    override = os.environ.get("AFRIPLAN_PROFILE")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".afriplan" / "profile.json"


def load_contractor_profile(path: Optional[Path] = None) -> ContractorProfile:
    """
    Load the saved profile, or return a default one if no file exists
    or the file is unreadable / invalid.
    """
    p = Path(path) if path else default_profile_path()
    if not p.exists():
        return ContractorProfile()

    try:
        with p.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        return ContractorProfile.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValidationError) as e:
        log.warning("Could not load contractor profile from %s: %s", p, e)
        return ContractorProfile()


def save_contractor_profile(
    profile: ContractorProfile,
    path: Optional[Path] = None,
) -> Optional[Path]:
    """
    Persist the profile to disk. Returns the path on success, None on failure.
    """
    p = Path(path) if path else default_profile_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            f.write(profile.model_dump_json(indent=2))
        return p
    except OSError as e:
        log.warning("Could not save contractor profile to %s: %s", p, e)
        return None


def profile_exists(path: Optional[Path] = None) -> bool:
    p = Path(path) if path else default_profile_path()
    return p.exists()
