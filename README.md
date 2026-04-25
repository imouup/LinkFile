# LinkFile

LinkFile is a lightweight BYOS file sharing tool for AI workflows, temporary downloads, and personal direct links.

The project is initialized as a CLI-first monorepo with:

- `apps/api`: FastAPI backend for online sharing, metadata, sync, and server local-storage.
- `apps/web`: Astro web app shell.
- `apps/cli`: Typer CLI for offline-first local workflows.
- `packages/py-core`: shared storage, crypto, config, local index, and local-server logic.
- `packages/py-sdk`: Python SDK for online and local clients.

## Development

Python packages are managed with `uv`.

```bash
uv sync --all-packages
uv run linkfile --help
uv run uvicorn linkfile_api.main:app --app-dir apps/api
```

The v0.1 target is the offline CLI loop: local setup, S3-compatible storage, Cloudreve storage, temporary local-server sharing, and a local SQLite index. Temporary direct URLs must be generated on demand and never persisted.
