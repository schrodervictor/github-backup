"""Downloader for container/docker images via GHCR OCI API."""

import logging
from typing import Any

from .. import config
from ..client import GitHubClient
from ..utils import save_binary, save_json
from . import downloader

logger = logging.getLogger(__name__)

GHCR_URL = "https://ghcr.io"

OCI_ACCEPT = ", ".join(
    [
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
    ]
)


@downloader("container", "docker")
def download(
    client: GitHubClient,
    pkg_name: str,
    version_name: str,
    version: dict[str, Any],
    version_dir: str,
) -> None:
    """Download a container image manifest and all blobs via GHCR OCI API."""
    tags = version.get("metadata", {}).get("container", {}).get("tags", [])
    digest = version_name  # usually sha256:...

    # Prefer digest for deterministic fetches, fall back to first tag
    reference = (
        digest
        if digest.startswith("sha256:")
        else (tags[0] if tags else digest)
    )

    manifest_url = f"{GHCR_URL}/v2/{client.owner}/{pkg_name}/manifests/{reference}"
    auth_headers = {"Authorization": f"Bearer {client.token}"}

    logger.info("    Fetching container manifest: %s", reference[:40])
    resp = client.get(
        manifest_url, headers={**auth_headers, "Accept": OCI_ACCEPT}
    )
    if resp.status_code != 200:
        logger.warning("    Failed to fetch manifest (%d)", resp.status_code)
        return

    manifest = resp.json()
    save_json(config.get("base_dir"), f"{version_dir}/manifest.json", manifest)

    media_type = manifest.get("mediaType", "")

    # If this is a multi-arch index, download each platform manifest
    if "index" in media_type or "manifest.list" in media_type:
        for entry in manifest.get("manifests", []):
            entry_digest = entry.get("digest", "")
            platform = entry.get("platform", {})
            platform_label = (
                f"{platform.get('os', 'unknown')}"
                f"_{platform.get('architecture', 'unknown')}"
            )
            entry_dir = f"{version_dir}/platforms/{platform_label}"

            entry_url = (
                f"{GHCR_URL}/v2/{client.owner}/{pkg_name}/manifests/{entry_digest}"
            )
            entry_resp = client.get(
                entry_url, headers={**auth_headers, "Accept": OCI_ACCEPT}
            )
            if entry_resp.status_code == 200:
                entry_manifest = entry_resp.json()
                save_json(
                    config.get("base_dir"),
                    f"{entry_dir}/manifest.json",
                    entry_manifest,
                )
                _download_manifest_blobs(
                    client, pkg_name, entry_manifest, entry_dir, auth_headers
                )
    else:
        _download_manifest_blobs(
            client, pkg_name, manifest, version_dir, auth_headers
        )


def _download_manifest_blobs(
    client: GitHubClient,
    pkg_name: str,
    manifest: dict[str, Any],
    version_dir: str,
    auth_headers: dict[str, str],
) -> None:
    """Download config and layer blobs referenced by a container manifest."""
    config_desc = manifest.get("config")
    if config_desc:
        _download_blob(client, pkg_name, config_desc, version_dir, auth_headers)

    for layer in manifest.get("layers", []):
        _download_blob(client, pkg_name, layer, version_dir, auth_headers)


def _download_blob(
    client: GitHubClient,
    pkg_name: str,
    descriptor: dict[str, Any],
    version_dir: str,
    auth_headers: dict[str, str],
) -> None:
    digest = descriptor.get("digest", "")
    if not digest:
        return

    blob_url = f"{GHCR_URL}/v2/{client.owner}/{pkg_name}/blobs/{digest}"
    logger.info("      Downloading blob: %s...", digest[:24])
    resp = client.get(blob_url, stream=True, headers=auth_headers)
    if resp.status_code == 200:
        safe_digest = digest.replace(":", "_")
        save_binary(
            config.get("base_dir"), f"{version_dir}/blobs/{safe_digest}", resp
        )
    else:
        logger.warning(
            "      Failed to download blob %s (%d)", digest[:24], resp.status_code
        )
