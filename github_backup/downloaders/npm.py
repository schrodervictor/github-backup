"""Downloader for npm packages from GitHub Packages npm registry."""

import logging
from typing import Any

from .. import config
from ..client import GitHubClient
from ..utils import save_binary, save_json
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

    # Fetch package metadata from the registry to get the real tarball URL
    metadata_url = f"{REGISTRY_URL}/@{client.owner}/{pkg_name}"
    logger.info("    Fetching npm metadata: @%s/%s", client.owner, pkg_name)
    meta_resp = client.get(metadata_url, headers=auth_headers)
    if meta_resp.status_code != 200:
        logger.warning(
            "    Failed to fetch npm metadata (%d)", meta_resp.status_code
        )
        return

    metadata = meta_resp.json()
    save_json(config.get("base_dir"), f"{version_dir}/metadata.json", metadata)

    version_meta = metadata.get("versions", {}).get(version_name)
    if not version_meta:
        logger.warning("    Version %s not found in registry metadata", version_name)
        return

    tarball_url = version_meta.get("dist", {}).get("tarball")
    if not tarball_url:
        logger.warning("    No tarball URL in registry metadata for %s", version_name)
        return

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
