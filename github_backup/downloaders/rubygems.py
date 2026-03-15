"""Downloader for gems from GitHub Packages RubyGems registry."""

import logging
from typing import Any

from .. import config
from ..client import GitHubClient
from ..utils import save_binary, save_json
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
    """Download a gem by fetching metadata from the RubyGems API first."""
    auth_headers = {"Authorization": f"Bearer {client.token}"}

    # Fetch gem metadata from the Bundler API to discover the download URL
    metadata_url = f"{REGISTRY_URL}/{client.owner}/api/v1/gems/{pkg_name}.json"
    logger.info("    Fetching gem metadata: %s", pkg_name)
    meta_resp = client.get(metadata_url, headers=auth_headers)
    if meta_resp.status_code != 200:
        logger.warning(
            "    Failed to fetch gem metadata (%d)", meta_resp.status_code
        )
        return

    metadata = meta_resp.json()
    save_json(config.get("base_dir"), f"{version_dir}/metadata.json", metadata)

    # The gem_uri field contains the download URL
    gem_url = metadata.get("gem_uri")
    if not gem_url:
        logger.warning("    No gem_uri in metadata for %s", pkg_name)
        return

    logger.info("    Downloading gem: %s@%s", pkg_name, version_name)
    resp = client.get(gem_url, stream=True, headers=auth_headers)
    if resp.status_code == 200:
        filename = f"{pkg_name}-{version_name}.gem"
        save_binary(config.get("base_dir"), f"{version_dir}/{filename}", resp)
    else:
        logger.warning("    Failed to download gem (%d)", resp.status_code)
