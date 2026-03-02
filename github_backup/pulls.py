"""Backup for pull requests with diffs, comments, reviews, and reactions."""

import logging
from typing import Any

from . import config
from .client import API_BASE, GitHubClient
from .reactions import save_comment_reactions, save_reactions
from .utils import save_json, save_text

logger = logging.getLogger(__name__)


def backup(client: GitHubClient) -> None:
    logger.info("Fetching pull requests...")
    pulls = client.paginate(
        f"{client.repo_path}/pulls",
        params={"state": "all", "direction": "asc"},
    )
    logger.info(f"  {len(pulls)} pull requests")
    save_json(config.get("base_dir"), "pulls/index.json", pulls)

    for pr in pulls:
        n = pr["number"]
        logger.info(f"  PR #{n}...")
        _backup_single_pr(client, n, pr)


def _backup_single_pr(client: GitHubClient, n: int, pr: dict[str, Any]) -> None:
    rp = client.repo_path
    save_json(config.get("base_dir"), f"pulls/{n}/pull.json", pr)

    _backup_diff(client, n)
    save_reactions(client, f"{rp}/issues/{n}", f"pulls/{n}/reactions.json", parent=pr)
    _backup_comments(client, n)
    _backup_reviews(client, n)
    _backup_review_comments(client, n)

    commits = client.paginate(f"{rp}/pulls/{n}/commits")
    save_json(config.get("base_dir"), f"pulls/{n}/commits.json", commits)


def _backup_diff(client: GitHubClient, n: int) -> None:
    resp = client.get(
        f"{API_BASE}{client.repo_path}/pulls/{n}",
        headers={"Accept": "application/vnd.github.diff"},
    )
    if resp.status_code == 200:
        save_text(config.get("base_dir"), f"pulls/{n}/diff.patch", resp.text)


def _backup_comments(client: GitHubClient, n: int) -> None:
    """Conversation comments (issue-style) and their reactions."""
    rp = client.repo_path
    comments = client.paginate(f"{rp}/issues/{n}/comments")
    save_json(config.get("base_dir"), f"pulls/{n}/comments.json", comments)
    save_comment_reactions(
        client,
        comments,
        api_tpl=f"{rp}/issues/comments/{{cid}}",
        save_tpl=f"pulls/{n}/comments/{{cid}}/reactions.json",
    )


def _backup_reviews(client: GitHubClient, n: int) -> None:
    """Reviews, their reactions, and per-review comments."""
    rp = client.repo_path
    reviews = client.paginate(f"{rp}/pulls/{n}/reviews")
    save_json(config.get("base_dir"), f"pulls/{n}/reviews.json", reviews)

    for review in reviews:
        rid = review["id"]
        save_reactions(
            client,
            f"{rp}/pulls/{n}/reviews/{rid}",
            f"pulls/{n}/reviews/{rid}/reactions.json",
            parent=review,
        )
        rev_comments = client.paginate(
            f"{rp}/pulls/{n}/reviews/{rid}/comments"
        )
        if rev_comments:
            save_json(
                config.get("base_dir"),
                f"pulls/{n}/reviews/{rid}/comments.json",
                rev_comments,
            )


def _backup_review_comments(client: GitHubClient, n: int) -> None:
    """All inline diff comments and their reactions."""
    rp = client.repo_path
    review_comments = client.paginate(f"{rp}/pulls/{n}/comments")
    save_json(config.get("base_dir"), f"pulls/{n}/review_comments.json", review_comments)
    save_comment_reactions(
        client,
        review_comments,
        api_tpl=f"{rp}/pulls/comments/{{cid}}",
        save_tpl=f"pulls/{n}/review_comments/{{cid}}/reactions.json",
    )
