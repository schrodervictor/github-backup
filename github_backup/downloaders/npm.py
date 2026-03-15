"""Downloader for npm packages from GitHub Packages npm registry."""

import logging
from typing import Any

from .. import config
from ..client import GitHubClient
from ..utils import save_binary
from . import downloader

logger = logging.getLogger(__name__)

REGISTRY_URL = "https://npm.pkg.github.com"


@downloader("npm")
def download(
    client: GitHubClient,
    pkg_name: str,
    version_name: str,
    version: dict[str, Any],
    version_dir: str,
) -> None:
    """Download an npm package tarball from GitHub Packages npm registry."""
    auth_headers = {"Authorization": f"Bearer {client.token}"}

    # GitHub npm packages are always scoped under @owner
    tarball_url = (
        f"{REGISTRY_URL}/@{client.owner}/{pkg_name}/-/{pkg_name}-{version_name}.tgz"
    )
    logger.info("    Downloading npm tarball: %s@%s", pkg_name, version_name)
    resp = client.get(tarball_url, stream=True, headers=auth_headers)
    if resp.status_code == 200:
        save_binary(
            config.get("base_dir"),
            f"{version_dir}/{pkg_name}-{version_name}.tgz",
            resp,
        )
    else:
        logger.warning("    Failed to download npm package (%d)", resp.status_code)
