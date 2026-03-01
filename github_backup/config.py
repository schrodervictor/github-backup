"""Centralized configuration for the backup tool."""

import os
import re
import subprocess
import sys
from typing import Any

_config: dict[str, Any] = {}


def init(base_dir: str) -> None:
    """Initialize configuration. Must be called once at startup."""
    _config["base_dir"] = base_dir


def get(key: str) -> Any:
    """Get a configuration value by key."""
    return _config[key]


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
