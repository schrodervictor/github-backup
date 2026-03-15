"""Backup for GitHub Discussions via GraphQL API."""

import logging
from typing import Any

from . import config
from .client import GitHubClient
from .utils import merge_json_list, save_json

logger = logging.getLogger(__name__)


def backup(client: GitHubClient) -> None:
    since = config.get("since")
    logger.info("Fetching discussions (GraphQL)%s...", f" (since {since})" if since else "")
    discussions = _fetch_all_discussions(client, since=since)
    logger.info(f"  {len(discussions)} discussions")

    for disc in discussions:
        n = disc["number"]
        logger.info(f"  Discussion #{n}...")
        disc["comments"] = _fetch_comments(client, disc["id"])
        save_json(config.get("base_dir"), f"discussions/{n}/discussion.json", disc)

    if since:
        merge_json_list(config.get("base_dir"), "discussions/index.json", discussions)
    else:
        save_json(config.get("base_dir"), "discussions/index.json", discussions)


def _fetch_all_discussions(
    client: GitHubClient, since: str | None = None,
) -> list[dict[str, Any]]:
    discussions: list[dict[str, Any]] = []
    cursor: str | None = None

    while True:
        data = client.graphql(
            """
            query($owner: String!, $repo: String!, $after: String) {
              repository(owner: $owner, name: $repo) {
                discussions(first: 50, after: $after, orderBy: {field: UPDATED_AT, direction: DESC}) {
                  pageInfo { hasNextPage endCursor }
                  nodes {
                    id
                    number
                    title
                    body
                    author { login }
                    createdAt
                    updatedAt
                    category { name }
                    labels(first: 20) { nodes { name } }
                  }
                }
              }
            }
            """,
            {"owner": client.owner, "repo": client.repo, "after": cursor},
        )
        if not data:
            break
        disc_data = data["repository"]["discussions"]
        page_nodes = disc_data["nodes"]

        if since:
            # Ordered by UPDATED_AT DESC, so once we see a discussion older
            # than `since`, all remaining ones are also older — stop early.
            for node in page_nodes:
                if node["updatedAt"] >= since:
                    discussions.append(node)
                else:
                    return discussions
        else:
            discussions.extend(page_nodes)

        if disc_data["pageInfo"]["hasNextPage"]:
            cursor = disc_data["pageInfo"]["endCursor"]
        else:
            break

    return discussions


def _fetch_comments(client: GitHubClient, discussion_id: str) -> list[dict[str, Any]]:
    all_comments: list[dict[str, Any]] = []
    cursor: str | None = None

    while True:
        data = client.graphql(
            """
            query($id: ID!, $after: String) {
              node(id: $id) {
                ... on Discussion {
                  comments(first: 100, after: $after) {
                    pageInfo { hasNextPage endCursor }
                    nodes {
                      id
                      body
                      author { login }
                      createdAt
                      replies(first: 10) {
                        pageInfo { hasNextPage }
                        nodes {
                          id
                          body
                          author { login }
                          createdAt
                        }
                      }
                    }
                  }
                }
              }
            }
            """,
            {"id": discussion_id, "after": cursor},
        )
        if not data or not data.get("node"):
            break
        comments_data = data["node"]["comments"]
        for comment in comments_data["nodes"]:
            if comment["replies"]["pageInfo"]["hasNextPage"]:
                comment["replies"]["nodes"] = _fetch_replies(client, comment["id"])
            all_comments.append(comment)
        if comments_data["pageInfo"]["hasNextPage"]:
            cursor = comments_data["pageInfo"]["endCursor"]
        else:
            break

    return all_comments


def _fetch_replies(client: GitHubClient, comment_id: str) -> list[dict[str, Any]]:
    all_replies: list[dict[str, Any]] = []
    cursor: str | None = None

    while True:
        data = client.graphql(
            """
            query($id: ID!, $after: String) {
              node(id: $id) {
                ... on DiscussionComment {
                  replies(first: 100, after: $after) {
                    pageInfo { hasNextPage endCursor }
                    nodes {
                      id
                      body
                      author { login }
                      createdAt
                    }
                  }
                }
              }
            }
            """,
            {"id": comment_id, "after": cursor},
        )
        if not data or not data.get("node"):
            break
        replies = data["node"]["replies"]
        all_replies.extend(replies["nodes"])
        if replies["pageInfo"]["hasNextPage"]:
            cursor = replies["pageInfo"]["endCursor"]
        else:
            break

    return all_replies
