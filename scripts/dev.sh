#!/usr/bin/env sh
set -eu

uv run uvicorn linkfile_api.main:app --app-dir apps/api --reload
