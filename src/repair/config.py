from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    parent = config.get("extends")
    if not parent:
        return config
    base_path = (config_path.parent / parent).resolve()
    base = load_config(base_path)
    local = dict(config)
    local.pop("extends", None)
    return _merge_dicts(base, local)

