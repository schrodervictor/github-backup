"""Downloader for NuGet packages from GitHub Packages NuGet registry."""

import logging
from typing import Any

from .. import config
from ..client import GitHubClient
from ..utils import save_binary, save_json
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
    """Download a NuGet package by discovering the base address from the service index."""
    auth_headers = {"Authorization": f"Bearer {client.token}"}

    base_address = _get_package_base_address(client, auth_headers)
    if not base_address:
        return

    # NuGet V3 protocol: package IDs and versions are lowercased in URLs
    lower_id = pkg_name.lower()
    lower_version = version_name.lower()

    nupkg_url = (
        f"{base_address}{lower_id}/{lower_version}/{lower_id}.{lower_version}.nupkg"
    )
    logger.info("    Downloading NuGet package: %s@%s", pkg_name, version_name)
    resp = client.get(nupkg_url, stream=True, headers=auth_headers)
    if resp.status_code == 200:
        filename = f"{pkg_name}.{version_name}.nupkg"
        save_binary(config.get("base_dir"), f"{version_dir}/{filename}", resp)
    else:
        logger.warning("    Failed to download NuGet package (%d)", resp.status_code)

    # Also fetch the nuspec for metadata
    nuspec_url = (
        f"{base_address}{lower_id}/{lower_version}/{lower_id}.nuspec"
    )
    nuspec_resp = client.get(nuspec_url, headers=auth_headers)
    if nuspec_resp.status_code == 200:
        save_json(
            config.get("base_dir"),
            f"{version_dir}/nuspec.json",
            nuspec_resp.json() if nuspec_resp.headers.get("content-type", "").startswith("application/json") else {"raw": nuspec_resp.text},
        )


def _get_package_base_address(
    client: GitHubClient, auth_headers: dict[str, str]
) -> str | None:
    """Discover the PackageBaseAddress from the NuGet V3 service index."""
    index_url = f"{REGISTRY_URL}/{client.owner}/index.json"
    logger.info("    Fetching NuGet service index...")
    resp = client.get(index_url, headers=auth_headers)
    if resp.status_code != 200:
        logger.warning("    Failed to fetch NuGet service index (%d)", resp.status_code)
        return None

    index = resp.json()
    for resource in index.get("resources", []):
        if resource.get("@type") == "PackageBaseAddress/3.0.0":
            url = resource["@id"]
            # Ensure trailing slash
            return url if url.endswith("/") else url + "/"

    logger.warning("    PackageBaseAddress not found in NuGet service index")
    return None
