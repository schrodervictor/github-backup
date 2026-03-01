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
