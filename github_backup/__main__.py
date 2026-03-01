#!/usr/bin/env python3
"""
GitHub Repository Data Backup

Backs up all non-git data from a GitHub repository into the .github
directory of the current repository.

Usage:
    python -m github_backup [--token TOKEN] [--output-dir DIR]

Run from within a git repository with a GitHub origin remote.
The token can also be set via the GITHUB_TOKEN environment variable.

Requires Python 3.10+.
"""

import sys

if sys.version_info < (3, 10):
    sys.exit("Error: github_backup requires Python 3.10 or later.")

import argparse
import logging
import os
from types import ModuleType

from . import config
from .client import GitHubClient
from . import simple, issues, pulls, releases, workflows, discussions

logger = logging.getLogger(__name__)

STEP_REGISTRY: dict[str, ModuleType] = {
    "simple": simple,
    "issues": issues,
    "pulls": pulls,
    "releases": releases,
    "workflows": workflows,
    "discussions": discussions,
}

STEP_NAMES = list(STEP_REGISTRY.keys())


class _StepFilter(argparse.Action):
    """Collect --include/--exclude operations in order."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | None,
        option_string: str | None = None,
    ) -> None:
        ops: list[tuple[str, str]] = getattr(namespace, "step_filters", [])
        ops.append((self.dest, values))
        namespace.step_filters = ops


def _resolve_steps(filters: list[tuple[str, str]]) -> list[ModuleType]:
    """Apply include/exclude filters in order to produce the final step list.

    If the first filter is --include, start from an empty set.
    If the first filter is --exclude, start from the full set.
    """
    if not filters:
        return list(STEP_REGISTRY.values())

    if filters[0][0] == "include":
        selected = set[str]()
    else:
        selected = set(STEP_NAMES)

    for op, name in filters:
        if op == "include":
            selected.add(name)
        else:
            selected.discard(name)

    return [STEP_REGISTRY[name] for name in STEP_NAMES if name in selected]


def main() -> None:
    step_names_csv = ", ".join(STEP_NAMES)

    parser = argparse.ArgumentParser(
        description="Back up GitHub repository data (issues, PRs, discussions, etc.)"
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub personal access token (default: GITHUB_TOKEN env var)",
    )
    parser.add_argument(
        "--output-dir",
        default=".github",
        help="Output directory (default: .github)",
    )
    parser.add_argument(
        "--include",
        action=_StepFilter,
        dest="include",
        choices=STEP_NAMES,
        metavar="STEP",
        help=f"Include a backup step (can be repeated; choices: {step_names_csv})",
    )
    parser.add_argument(
        "--exclude",
        action=_StepFilter,
        dest="exclude",
        choices=STEP_NAMES,
        metavar="STEP",
        help=f"Exclude a backup step (can be repeated; choices: {step_names_csv})",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(message)s",
        stream=os.sys.stderr,
    )

    config.init(args.output_dir)

    if not args.token:
        parser.error(
            "A GitHub token is required. Use --token or set GITHUB_TOKEN env var."
        )

    steps = _resolve_steps(getattr(args, "step_filters", []))

    owner, repo = config.detect_repo()
    client = GitHubClient(owner, repo, args.token)

    base_dir = config.get("base_dir")
    logger.info("Backing up %s/%s → %s", owner, repo, base_dir)
    os.makedirs(base_dir, exist_ok=True)

    for step in steps:
        step.backup(client)

    logger.info("Backup complete → %s", base_dir)


if __name__ == "__main__":
    main()
