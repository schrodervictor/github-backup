"""Backup for simple, single-endpoint resources."""

import logging

from . import config
from .client import GitHubClient
from .utils import save_json

logger = logging.getLogger(__name__)


def backup(client: GitHubClient) -> None:
    _backup_metadata(client)
    _backup_labels(client)
    _backup_milestones(client)
    _backup_projects(client)
    _backup_commit_comments(client)


def _backup_metadata(client: GitHubClient) -> None:
    logger.info("Fetching repository metadata...")
    data = client.paginate(client.repo_path)
    save_json(config.get("base_dir"), "metadata.json", data)


def _backup_labels(client: GitHubClient) -> None:
    logger.info("Fetching labels...")
    data = client.paginate(f"{client.repo_path}/labels")
    logger.info(f"  {len(data)} labels")
    save_json(config.get("base_dir"), "labels.json", data)


def _backup_milestones(client: GitHubClient) -> None:
    logger.info("Fetching milestones...")
    data = client.paginate(
        f"{client.repo_path}/milestones",
        params={"state": "all"},
    )
    logger.info(f"  {len(data)} milestones")
    save_json(config.get("base_dir"), "milestones.json", data)


def _backup_projects(client: GitHubClient) -> None:
    logger.info("Fetching classic projects...")
    data = client.paginate(
        f"{client.repo_path}/projects",
        headers={"Accept": "application/vnd.github.inertia-preview+json"},
    )
    logger.info(f"  {len(data)} projects")
    save_json(config.get("base_dir"), "projects.json", data)


def _backup_commit_comments(client: GitHubClient) -> None:
    logger.info("Fetching commit comments...")
    data = client.paginate(f"{client.repo_path}/comments")
    logger.info(f"  {len(data)} commit comments")
    save_json(config.get("base_dir"), "commit_comments.json", data)
