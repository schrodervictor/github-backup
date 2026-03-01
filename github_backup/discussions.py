"""Backup for GitHub Discussions via GraphQL API."""

import logging
from typing import Any

from . import config
from .client import GitHubClient
from .utils import save_json

logger = logging.getLogger(__name__)


def backup(client: GitHubClient) -> None:
    logger.info("Fetching discussions (GraphQL)...")
    discussions = _fetch_all_discussions(client)
    logger.info(f"  {len(discussions)} discussions")

    for disc in discussions:
        n = disc["number"]
        logger.info(f"  Discussion #{n}...")
        disc["comments"] = _fetch_comments(client, disc["id"])
        save_json(config.get("base_dir"), f"discussions/{n}/discussion.json", disc)

    save_json(config.get("base_dir"), "discussions/index.json", discussions)


def _fetch_all_discussions(client: GitHubClient) -> list[dict[str, Any]]:
    discussions: list[dict[str, Any]] = []
    cursor: str | None = None

    while True:
        data = client.graphql(
            """
            query($owner: String!, $repo: String!, $after: String) {
              repository(owner: $owner, name: $repo) {
                discussions(first: 50, after: $after) {
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
        discussions.extend(disc_data["nodes"])
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
