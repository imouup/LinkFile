from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir


@dataclass(frozen=True)
class LinkFilePaths:
    config_dir: Path
    data_dir: Path
    config_file: Path
    index_file: Path


def get_default_paths(app_name: str = "linkfile") -> LinkFilePaths:
    config_dir = Path(os.environ.get("LINKFILE_CONFIG_DIR", user_config_dir(app_name)))
    data_dir = Path(os.environ.get("LINKFILE_DATA_DIR", user_data_dir(app_name)))
    return LinkFilePaths(
        config_dir=config_dir,
        data_dir=data_dir,
        config_file=config_dir / "config.json",
        index_file=data_dir / "index.sqlite3",
    )
