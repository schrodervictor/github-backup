"""Package downloaders registry.

Each submodule registers itself via the @downloader decorator at import time.
"""

from typing import Any, Callable

from ..client import GitHubClient

DownloaderFn = Callable[
    [GitHubClient, str, str, dict[str, Any], str],
    None,
]

_REGISTRY: dict[str, DownloaderFn] = {}


def downloader(*pkg_types: str):
    """Register a function as the downloader for one or more package types."""
    def decorator(fn: DownloaderFn) -> DownloaderFn:
        for pkg_type in pkg_types:
            _REGISTRY[pkg_type] = fn
        return fn
    return decorator


def get(pkg_type: str) -> DownloaderFn | None:
    """Look up the downloader for a package type."""
    return _REGISTRY.get(pkg_type)


# Import submodules to trigger registration
from . import container, npm, maven, nuget, rubygems  # noqa: E402, F401
