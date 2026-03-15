"""Downloader for gems from GitHub Packages RubyGems registry."""

import logging
from typing import Any

from .. import config
from ..client import GitHubClient
from ..utils import save_binary
from . import downloader

logger = logging.getLogger(__name__)

REGISTRY_URL = "https://rubygems.pkg.github.com"


@downloader("rubygems")
def download(
    client: GitHubClient,
    pkg_name: str,
    version_name: str,
    version: dict[str, Any],
    version_dir: str,
) -> None:
    """Download a gem from GitHub Packages RubyGems registry."""
    auth_headers = {"Authorization": f"Bearer {client.token}"}

    gem_url = f"{REGISTRY_URL}/gems/{pkg_name}-{version_name}.gem"
    logger.info("    Downloading gem: %s@%s", pkg_name, version_name)
    resp = client.get(gem_url, stream=True, headers=auth_headers)
    if resp.status_code == 200:
        filename = f"{pkg_name}-{version_name}.gem"
        save_binary(config.get("base_dir"), f"{version_dir}/{filename}", resp)
    else:
        logger.warning("    Failed to download gem (%d)", resp.status_code)
