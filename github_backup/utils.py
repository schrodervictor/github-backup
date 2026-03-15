"""File save utilities."""

import json
import os
from typing import Any

import requests


def save_json(base_dir: str, relative_path: str, data: Any) -> None:
    path = os.path.join(base_dir, relative_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(base_dir: str, relative_path: str) -> Any:
    """Load a JSON file, returning None if it doesn't exist."""
    path = os.path.join(base_dir, relative_path)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_json_list(
    base_dir: str,
    relative_path: str,
    new_items: list[dict[str, Any]],
    key: str = "id",
) -> None:
    """Merge new_items into an existing JSON list file, keyed by `key`.

    Items from new_items overwrite existing items with the same key value.
    New items not present in the existing file are appended.
    """
    existing = load_json(base_dir, relative_path)
    if not isinstance(existing, list):
        save_json(base_dir, relative_path, new_items)
        return

    index = {item[key]: item for item in existing}
    for item in new_items:
        index[item[key]] = item
    merged = list(index.values())
    save_json(base_dir, relative_path, merged)


def save_text(base_dir: str, relative_path: str, text: str) -> None:
    path = os.path.join(base_dir, relative_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def save_binary(base_dir: str, relative_path: str, response: requests.Response) -> None:
    """Stream a requests response body to a file."""
    path = os.path.join(base_dir, relative_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
