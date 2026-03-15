"""Backup for GitHub Packages (container images, npm, maven, nuget, rubygems)."""

import logging
from typing import Any

from . import config, downloaders
from .client import API_BASE, GitHubClient
from .utils import merge_json_list, save_json

logger = logging.getLogger(__name__)

PACKAGE_TYPES = ["container", "npm", "maven", "nuget", "rubygems", "docker"]


def backup(client: GitHubClient) -> None:
    since = config.get("since")
    owner_type = _detect_owner_type(client)
    all_packages = _list_all_packages(client, owner_type)

    # Filter to packages linked to the current repo
    repo_packages = [
        p
        for p in all_packages
        if (p.get("repository") or {}).get("name") == client.repo
    ]

    logger.info(
        "%d packages linked to %s/%s", len(repo_packages), client.owner, client.repo
    )

    if not repo_packages:
        return

    if since:
        merge_json_list(config.get("base_dir"), "packages/index.json", repo_packages)
    else:
        save_json(config.get("base_dir"), "packages/index.json", repo_packages)

    for package in repo_packages:
        _backup_package(client, owner_type, package, since)


def _detect_owner_type(client: GitHubClient) -> str:
    """Detect whether the repository owner is an org or a user."""
    resp = client.get(f"{API_BASE}/orgs/{client.owner}")
    if resp.status_code == 200:
        return "orgs"
    return "users"


def _list_all_packages(
    client: GitHubClient, owner_type: str
) -> list[dict[str, Any]]:
    """List all packages across every package type for the owner."""
    since = config.get("since")
    logger.info("Fetching packages%s...", f" (since {since})" if since else "")
    all_packages: list[dict[str, Any]] = []

    for pkg_type in PACKAGE_TYPES:
        packages = client.paginate(
            f"/{owner_type}/{client.owner}/packages",
            params={"package_type": pkg_type},
        )
        if isinstance(packages, list):
            all_packages.extend(packages)

    logger.info("  %d total packages found for %s", len(all_packages), client.owner)
    return all_packages


def _backup_package(
    client: GitHubClient,
    owner_type: str,
    package: dict[str, Any],
    since: str | None,
) -> None:
    pkg_type = package["package_type"]
    pkg_name = package["name"]
    safe_name = pkg_name.replace("/", "_")

    logger.info("  Backing up package: %s (%s)", pkg_name, pkg_type)
    pkg_dir = f"packages/{pkg_type}/{safe_name}"
    save_json(config.get("base_dir"), f"{pkg_dir}/package.json", package)

    versions = client.paginate(
        f"/{owner_type}/{client.owner}/packages/{pkg_type}/{pkg_name}/versions",
    )
    if not isinstance(versions, list):
        versions = []

    logger.info("    %d versions", len(versions))

    if since:
        versions = [
            v
            for v in versions
            if (v.get("updated_at") or v.get("created_at") or since) >= since
        ]
        logger.info("    %d new/updated since %s", len(versions), since)
        merge_json_list(config.get("base_dir"), f"{pkg_dir}/versions.json", versions)
    else:
        save_json(config.get("base_dir"), f"{pkg_dir}/versions.json", versions)

    for version in versions:
        _backup_version(client, pkg_type, pkg_name, safe_name, version)


def _backup_version(
    client: GitHubClient,
    pkg_type: str,
    pkg_name: str,
    safe_name: str,
    version: dict[str, Any],
) -> None:
    version_id = version["id"]
    version_name = version.get("name", str(version_id))
    safe_version = version_name.replace("/", "_")

    version_dir = f"packages/{pkg_type}/{safe_name}/{safe_version}"
    save_json(config.get("base_dir"), f"{version_dir}/version.json", version)

    download = downloaders.get(pkg_type)
    if download:
        download(client, pkg_name, version_name, version, version_dir)
