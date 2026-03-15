"""Backup for issues with comments, events, timeline, and reactions."""

import logging
from typing import Any

from . import config
from .client import GitHubClient
from .reactions import save_comment_reactions, save_reactions
from .utils import merge_json_list, save_json

logger = logging.getLogger(__name__)


def backup(client: GitHubClient) -> None:
    since = config.get("since")
    logger.info("Fetching issues%s...", f" (since {since})" if since else "")
    params: dict[str, str] = {"state": "all", "direction": "asc"}
    if since:
        params["since"] = since
    issues = client.paginate(
        f"{client.repo_path}/issues",
        params=params,
    )
    # The issues endpoint also returns PRs; separate them
    pure_issues = [i for i in issues if "pull_request" not in i]
    logger.info(f"  {len(pure_issues)} issues (excluding PRs)")
    if since:
        merge_json_list(config.get("base_dir"), "issues/index.json", pure_issues)
    else:
        save_json(config.get("base_dir"), "issues/index.json", pure_issues)

    for issue in pure_issues:
        n = issue["number"]
        logger.info(f"  Issue #{n}...")
        _backup_single_issue(client, n, issue)


def _backup_single_issue(client: GitHubClient, n: int, issue: dict[str, Any]) -> None:
    rp = client.repo_path
    save_json(config.get("base_dir"), f"issues/{n}/issue.json", issue)

    save_reactions(client, f"{rp}/issues/{n}", f"issues/{n}/reactions.json", parent=issue)

    comments = client.paginate(f"{rp}/issues/{n}/comments")
    save_json(config.get("base_dir"), f"issues/{n}/comments.json", comments)
    save_comment_reactions(
        client,
        comments,
        api_tpl=f"{rp}/issues/comments/{{cid}}",
        save_tpl=f"issues/{n}/comments/{{cid}}/reactions.json",
    )

    events = client.paginate(f"{rp}/issues/{n}/events")
    save_json(config.get("base_dir"), f"issues/{n}/events.json", events)

    timeline = client.paginate(
        f"{rp}/issues/{n}/timeline",
        headers={"Accept": "application/vnd.github.mockingbird-preview+json"},
    )
    save_json(config.get("base_dir"), f"issues/{n}/timeline.json", timeline)
