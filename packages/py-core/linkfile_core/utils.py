from __future__ import annotations

import hashlib
import mimetypes
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

_DURATION_PATTERN = re.compile(r"^(?P<value>\d+)(?P<unit>[smhd])$")


def parse_duration(value: str | None, *, default_seconds: int = 3600) -> timedelta:
    if not value:
        return timedelta(seconds=default_seconds)
    match = _DURATION_PATTERN.match(value.strip().lower())
    if not match:
        raise ValueError("Duration must use one of these suffixes: s, m, h, d.")
    amount = int(match.group("value"))
    unit = match.group("unit")
    if unit == "s":
        return timedelta(seconds=amount)
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    return timedelta(days=amount)


def expires_at_from_duration(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.now(UTC) + parse_duration(value)


def duration_seconds(value: str | None, *, default_seconds: int = 3600) -> int:
    return int(parse_duration(value, default_seconds=default_seconds).total_seconds())


def guess_mime_type(path: Path) -> str | None:
    mime_type, _ = mimetypes.guess_type(path.name)
    return mime_type


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
