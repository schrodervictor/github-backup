"""Centralized configuration for the backup tool."""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

_config: dict[str, Any] = {}

MARKER_FILE = "last_backup.json"


def init(base_dir: str, since: str | None = None) -> None:
    """Initialize configuration. Must be called once at startup."""
    _config["base_dir"] = base_dir
    _config["since"] = since


def get(key: str) -> Any:
    """Get a configuration value by key."""
    return _config[key]


def read_last_backup_timestamp(base_dir: str) -> str | None:
    """Read the timestamp from the last backup marker file."""
    marker_path = os.path.join(base_dir, MARKER_FILE)
    if not os.path.exists(marker_path):
        return None
    with open(marker_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("timestamp")


def write_last_backup_timestamp(base_dir: str) -> None:
    """Write the current UTC timestamp to the marker file."""
    marker_path = os.path.join(base_dir, MARKER_FILE)
    os.makedirs(os.path.dirname(marker_path) or ".", exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(marker_path, "w", encoding="utf-8") as f:
        json.dump({"timestamp": timestamp}, f, indent=2)


def detect_repo() -> tuple[str, str]:
    """Detect owner/repo from the git remote of the current directory.

    Returns (owner, repo) or exits with an error if detection fails.
    """
    try:
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: not a git repository or no 'origin' remote found.", file=sys.stderr)
        sys.exit(1)

    # Match SSH (git@github.com:owner/repo.git) or HTTPS (https://github.com/owner/repo.git)
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", url)
    if not match:
        print(f"Error: could not parse GitHub owner/repo from remote URL: {url}", file=sys.stderr)
        sys.exit(1)

    return match.group(1), match.group(2)
