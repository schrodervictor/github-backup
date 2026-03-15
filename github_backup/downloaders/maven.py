"""Downloader for Maven packages from GitHub Packages Maven registry."""

import logging
from typing import Any

from .. import config
from ..client import GitHubClient
from ..utils import save_binary
from . import downloader

logger = logging.getLogger(__name__)

REGISTRY_URL = "https://maven.pkg.github.com"


@downloader("maven")
def download(
    client: GitHubClient,
    pkg_name: str,
    version_name: str,
    version: dict[str, Any],
    version_dir: str,
) -> None:
    """Download a Maven JAR from GitHub Packages Maven registry."""
    auth_headers = {"Authorization": f"Bearer {client.token}"}

    # GitHub Maven packages use the naming convention: group.artifact
    # e.g. "com.example.mylib" -> group=com/example, artifact=mylib
    parts = pkg_name.rsplit(".", 1)
    if len(parts) == 2:
        group_path = parts[0].replace(".", "/")
        artifact = parts[1]
    else:
        group_path = client.owner
        artifact = pkg_name

    jar_url = (
        f"{REGISTRY_URL}/{client.owner}/{client.repo}/"
        f"{group_path}/{artifact}/{version_name}/{artifact}-{version_name}.jar"
    )
    logger.info("    Downloading Maven JAR: %s@%s", pkg_name, version_name)
    resp = client.get(jar_url, stream=True, headers=auth_headers)
    if resp.status_code == 200:
        save_binary(
            config.get("base_dir"),
            f"{version_dir}/{artifact}-{version_name}.jar",
            resp,
        )
    else:
        logger.warning("    Failed to download Maven package (%d)", resp.status_code)
