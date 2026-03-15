"""Downloader for Maven packages from GitHub Packages Maven registry."""

import logging
import re
from typing import Any

from .. import config
from ..client import GitHubClient
from ..utils import save_binary, save_text
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
    """Download Maven artifacts by fetching the POM to discover the packaging type."""
    auth_headers = {"Authorization": f"Bearer {client.token}"}

    group_id, artifact_id = _resolve_coordinates(pkg_name, version)
    group_path = group_id.replace(".", "/")

    base_url = (
        f"{REGISTRY_URL}/{client.owner}/{client.repo}"
        f"/{group_path}/{artifact_id}/{version_name}"
    )

    # Fetch the POM first — it tells us the packaging type and is useful metadata
    pom_url = f"{base_url}/{artifact_id}-{version_name}.pom"
    logger.info("    Fetching Maven POM: %s:%s:%s", group_id, artifact_id, version_name)
    pom_resp = client.get(pom_url, headers=auth_headers)
    if pom_resp.status_code != 200:
        logger.warning("    Failed to fetch POM (%d)", pom_resp.status_code)
        return

    pom_text = pom_resp.text
    save_text(
        config.get("base_dir"),
        f"{version_dir}/{artifact_id}-{version_name}.pom",
        pom_text,
    )

    # Extract packaging from POM (defaults to jar per Maven convention)
    packaging = _extract_packaging(pom_text)

    artifact_url = f"{base_url}/{artifact_id}-{version_name}.{packaging}"
    logger.info(
        "    Downloading Maven artifact: %s:%s:%s (%s)",
        group_id, artifact_id, version_name, packaging,
    )
    resp = client.get(artifact_url, stream=True, headers=auth_headers)
    if resp.status_code == 200:
        filename = f"{artifact_id}-{version_name}.{packaging}"
        save_binary(config.get("base_dir"), f"{version_dir}/{filename}", resp)
    else:
        logger.warning("    Failed to download Maven artifact (%d)", resp.status_code)


def _resolve_coordinates(
    pkg_name: str, version: dict[str, Any]
) -> tuple[str, str]:
    """Resolve Maven groupId and artifactId from version metadata or package name."""
    # The GitHub API version metadata may include Maven coordinates
    meta = version.get("metadata", {})
    if isinstance(meta, dict):
        group_id = meta.get("group_id") or meta.get("groupId")
        artifact_id = meta.get("artifact_id") or meta.get("artifactId")
        if group_id and artifact_id:
            return group_id, artifact_id

    # Fall back to splitting package name on the last dot
    parts = pkg_name.rsplit(".", 1)
    if len(parts) == 2:
        return parts[0], parts[1]

    return pkg_name, pkg_name


def _extract_packaging(pom_text: str) -> str:
    """Extract the <packaging> value from a POM XML string."""
    match = re.search(r"<packaging>\s*(\S+)\s*</packaging>", pom_text)
    if match:
        return match.group(1)
    # Maven defaults to jar when <packaging> is omitted
    return "jar"
