from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from linkfile_core.config.paths import LinkFilePaths, get_default_paths


def default_config() -> dict[str, Any]:
    return {
        "version": 1,
        "mode": "local_only",
        "server": {"enabled": False, "url": "https://api.linkfile.nyaku.moe"},
        "storage_methods": [],
        "defaults": {"storage_method_id": None},
    }


def ensure_local_environment(paths: LinkFilePaths | None = None) -> LinkFilePaths:
    paths = paths or get_default_paths()
    paths.config_dir.mkdir(parents=True, exist_ok=True)
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    if not paths.config_file.exists():
        save_config(default_config(), paths.config_file)
    return paths


def load_config(config_file: Path | None = None) -> dict[str, Any]:
    path = config_file or get_default_paths().config_file
    if not path.exists():
        ensure_local_environment(get_default_paths())
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(config: dict[str, Any], config_file: Path | None = None) -> None:
    path = config_file or get_default_paths().config_file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_storage_method(config: dict[str, Any], name_or_id: str | None) -> dict[str, Any]:
    methods = config.get("storage_methods", [])
    target = name_or_id or config.get("defaults", {}).get("storage_method_id")
    if not target:
        raise KeyError(
            "No storage method was provided and no default storage method is configured."
        )
    for method in methods:
        if method.get("id") == target or method.get("name") == target:
            return method
    raise KeyError(f"Storage method not found: {target}")


def upsert_storage_method(config: dict[str, Any], method: dict[str, Any]) -> dict[str, Any]:
    methods = list(config.get("storage_methods", []))
    replaced = False
    for index, existing in enumerate(methods):
        if existing.get("id") == method.get("id") or existing.get("name") == method.get("name"):
            methods[index] = method
            replaced = True
            break
    if not replaced:
        methods.append(method)
    config["storage_methods"] = methods
    defaults = config.setdefault("defaults", {})
    if not defaults.get("storage_method_id"):
        defaults["storage_method_id"] = method["id"]
    return config


def remove_storage_method(config: dict[str, Any], name_or_id: str) -> dict[str, Any]:
    methods = list(config.get("storage_methods", []))
    kept_methods = [
        method
        for method in methods
        if method.get("id") != name_or_id and method.get("name") != name_or_id
    ]
    if len(kept_methods) == len(methods):
        raise KeyError(f"Storage method not found: {name_or_id}")

    config["storage_methods"] = kept_methods
    defaults = config.setdefault("defaults", {})
    deleted_default = defaults.get("storage_method_id") == name_or_id
    if not deleted_default:
        deleted_default = all(
            method.get("id") != defaults.get("storage_method_id")
            for method in kept_methods
        )
    defaults["storage_method_id"] = (
        kept_methods[0]["id"] if deleted_default and kept_methods else None
    )
    return config
