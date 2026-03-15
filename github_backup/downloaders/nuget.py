"""Downloader for NuGet packages from GitHub Packages NuGet registry."""

import logging
from typing import Any

from .. import config
from ..client import GitHubClient
from ..utils import save_binary
from . import downloader

logger = logging.getLogger(__name__)

REGISTRY_URL = "https://nuget.pkg.github.com"


@downloader("nuget")
def download(
    client: GitHubClient,
    pkg_name: str,
    version_name: str,
    version: dict[str, Any],
    version_dir: str,
) -> None:
    """Download a NuGet package (.nupkg) from GitHub Packages NuGet registry."""
    auth_headers = {"Authorization": f"Bearer {client.token}"}

    nupkg_url = (
        f"{REGISTRY_URL}/{client.owner}/download/"
        f"{pkg_name}/{version_name}/{pkg_name}.{version_name}.nupkg"
    )
    logger.info("    Downloading NuGet package: %s@%s", pkg_name, version_name)
    resp = client.get(nupkg_url, stream=True, headers=auth_headers)
    if resp.status_code == 200:
        filename = f"{pkg_name}.{version_name}.nupkg"
        save_binary(config.get("base_dir"), f"{version_dir}/{filename}", resp)
    else:
        logger.warning("    Failed to download NuGet package (%d)", resp.status_code)
