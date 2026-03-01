"""Backup for releases with asset downloads."""

import logging
from typing import Any

from . import config
from .client import GitHubClient
from .utils import save_binary, save_json

logger = logging.getLogger(__name__)


def backup(client: GitHubClient) -> None:
    logger.info("Fetching releases...")
    releases = client.paginate(f"{client.repo_path}/releases")
    logger.info(f"  {len(releases)} releases")
    save_json(config.get("base_dir"), "releases/index.json", releases)

    for release in releases:
        tag = release.get("tag_name", str(release["id"]))
        safe_tag = tag.replace("/", "_")
        save_json(config.get("base_dir"), f"releases/{safe_tag}/release.json", release)

        for asset in release.get("assets", []):
            _download_asset(client, safe_tag, asset)


def _download_asset(client: GitHubClient, safe_tag: str, asset: dict[str, Any]) -> None:
    name = asset["name"]
    download_url = asset["browser_download_url"]
    logger.info(f"    Downloading asset: {name}...")
    resp = client.get(download_url, stream=True)
    if resp.status_code == 200:
        save_binary(config.get("base_dir"), f"releases/{safe_tag}/assets/{name}", resp)
    else:
        logger.warning("Failed to download %s (%d)", name, resp.status_code)
