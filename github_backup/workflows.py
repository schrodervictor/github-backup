"""Backup for GitHub Actions workflows and run history."""

import logging
from typing import Any

from . import config
from .client import API_BASE, PER_PAGE, GitHubClient
from .utils import merge_json_list, save_binary, save_json

logger = logging.getLogger(__name__)


def backup(client: GitHubClient) -> None:
    _backup_workflow_definitions(client)
    _backup_workflow_runs(client)


def _backup_workflow_definitions(client: GitHubClient) -> None:
    logger.info("Fetching Actions workflows...")
    data = client.paginate(f"{client.repo_path}/actions/workflows")
    if isinstance(data, dict):
        workflows = data.get("workflows", [])
    else:
        workflows = data
    logger.info(f"  {len(workflows)} workflows")
    save_json(config.get("base_dir"), "actions/workflows.json", workflows)


def _backup_workflow_runs(client: GitHubClient) -> None:
    since = config.get("since")
    logger.info("Fetching Actions workflow runs%s...", f" (since {since})" if since else "")
    all_runs: list[dict[str, Any]] = []
    page = 1

    params: dict[str, Any] = {"per_page": PER_PAGE, "page": page}
    if since:
        # The runs endpoint supports `created` filter with range syntax
        params["created"] = f">={since}"

    while True:
        params["page"] = page
        resp = client.get(
            f"{API_BASE}{client.repo_path}/actions/runs",
            params=params,
        )
        if resp.status_code == 404:
            logger.warning("404 — Actions not enabled, skipping")
            return
        resp.raise_for_status()
        data = resp.json()
        runs = data.get("workflow_runs", [])
        if not runs:
            break
        all_runs.extend(runs)
        if len(all_runs) >= data.get("total_count", 0):
            break
        page += 1

    logger.info(f"  {len(all_runs)} workflow runs")
    if since:
        merge_json_list(config.get("base_dir"), "actions/runs/index.json", all_runs)
    else:
        save_json(config.get("base_dir"), "actions/runs/index.json", all_runs)

    for run in all_runs:
        _backup_single_run(client, run)


def _backup_single_run(client: GitHubClient, run: dict[str, Any]) -> None:
    run_id = run["id"]
    save_json(config.get("base_dir"), f"actions/runs/{run_id}/run.json", run)

    jobs_resp = client.get(
        f"{API_BASE}{client.repo_path}/actions/runs/{run_id}/jobs",
        params={"per_page": PER_PAGE},
    )
    if jobs_resp.status_code == 200:
        jobs = jobs_resp.json().get("jobs", [])
        save_json(config.get("base_dir"), f"actions/runs/{run_id}/jobs.json", jobs)

    logs_resp = client.get(
        f"{API_BASE}{client.repo_path}/actions/runs/{run_id}/logs",
        stream=True,
    )
    if logs_resp.status_code == 200:
        save_binary(config.get("base_dir"), f"actions/runs/{run_id}/logs.zip", logs_resp)
