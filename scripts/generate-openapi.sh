#!/usr/bin/env sh
set -eu

uv run python -m linkfile_api.utils.openapi apps/api/openapi.json
