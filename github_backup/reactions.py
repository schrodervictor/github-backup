"""Helpers for fetching and saving reactions."""

from typing import Any

from . import config
from .client import GitHubClient
from .utils import save_json


def fetch_reactions(client: GitHubClient, endpoint: str) -> list[dict[str, Any]]:
    """Fetch all reactions for a given API endpoint."""
    return client.paginate(
        f"{endpoint}/reactions",
        headers={"Accept": "application/vnd.github.squirrel-girl-preview+json"},
    )


def save_reactions(
    client: GitHubClient,
    api_endpoint: str,
    save_path: str,
    parent: dict[str, Any],
) -> None:
    """Fetch reactions and save only if non-empty.

    Skips the API call entirely when the parent object reports zero reactions.
    """
    if parent.get("reactions", {}).get("total_count", 0) == 0:
        return
    reactions = fetch_reactions(client, api_endpoint)
    if reactions:
        save_json(config.get("base_dir"), save_path, reactions)


def save_comment_reactions(
    client: GitHubClient,
    comments: list[dict[str, Any]],
    api_tpl: str,
    save_tpl: str,
) -> None:
    """For each comment in a list, fetch and save its reactions.

    api_tpl and save_tpl should contain {cid} as placeholder.
    """
    for comment in comments:
        cid = comment["id"]
        save_reactions(
            client,
            api_tpl.format(cid=cid),
            save_tpl.format(cid=cid),
            parent=comment,
        )
