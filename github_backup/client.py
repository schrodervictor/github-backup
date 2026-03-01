"""HTTP client for the GitHub REST and GraphQL APIs."""

import logging
import re
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"
PER_PAGE = 100


class GitHubClient:
    def __init__(self, owner: str, repo: str, token: str) -> None:
        self.owner = owner
        self.repo = repo
        self.repo_path = f"/repos/{owner}/{repo}"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    # ── HTTP layer ──────────────────────────────────────────────────

    def _handle_rate_limit(self, response: requests.Response) -> None:
        remaining = int(response.headers.get("X-RateLimit-Remaining", 1))
        if remaining == 0:
            reset_at = int(response.headers.get("X-RateLimit-Reset", 0))
            wait = max(reset_at - int(time.time()), 1) + 1
            logger.warning("Rate limited. Sleeping %ds until reset...", wait)
            time.sleep(wait)

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        for attempt in range(3):
            resp = self.session.request(method, url, **kwargs)
            if resp.status_code == 403 and "rate limit" in resp.text.lower():
                self._handle_rate_limit(resp)
                continue
            if resp.status_code >= 500:
                wait = 2**attempt
                logger.warning("Server error %d, retrying in %ds...", resp.status_code, wait)
                time.sleep(wait)
                continue
            return resp
        return resp

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        return self._request("POST", url, **kwargs)

    def paginate(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Fetch all pages from a REST endpoint. Returns combined list."""
        url = f"{API_BASE}{endpoint}"
        if params is None:
            params = {}
        params["per_page"] = PER_PAGE
        all_items: list[dict[str, Any]] = []

        while url:
            resp = self.get(url, params=params, headers=headers)
            if resp.status_code in (404, 410, 422):
                logger.warning("%d for %s — skipping", resp.status_code, endpoint)
                return []
            resp.raise_for_status()
            self._handle_rate_limit(resp)
            data = resp.json()
            if isinstance(data, list):
                all_items.extend(data)
            else:
                return data
            link = resp.headers.get("Link", "")
            match = re.search(r'<([^>]+)>;\s*rel="next"', link)
            url = match.group(1) if match else None
            params = {}  # params are already in the next URL

        return all_items

    # ── GraphQL ─────────────────────────────────────────────────────

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any] | None:
        """Execute a GraphQL query. Returns data dict or None on error."""
        resp = self.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables},
        )
        if resp.status_code != 200:
            logger.warning("GraphQL HTTP error %d", resp.status_code)
            return None
        result = resp.json()
        if "errors" in result:
            logger.warning(
                "GraphQL errors: %s", result["errors"][0].get("message", "")
            )
            return None
        return result["data"]
