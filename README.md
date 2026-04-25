# LinkFile

Version: `0.1.1`

LinkFile is a lightweight BYOS file sharing tool for AI workflows, temporary downloads, and personal direct links.

The current release is CLI-first and implements Local Only mode. You bring your own storage, configure it locally, upload files from the command line, and get direct links that are easy to pass to AI tools, scripts, or other people.

Current storage support:

- S3-compatible storage, including Cloudflare R2 and MinIO
- Cloudreve v3/4

<div style="display:flex;flex-direction:row;gap:8px;">
<a href="/README.md">English</a>|
<a href="/README-CN.md">简体中文</a>
</div>

## Getting Started

### Installation

#### 1. Install from source

Install dependencies for the whole workspace:

```bash
git clone https://github.com/imouup/LinkFile.git
cd LinkFile
uv sync --all-packages
```

Check the CLI:

```bash
uv run --package linkfile-cli linkfile --help
```

If the workspace package has already been installed in your active virtual environment, you can also run:

```bash
linkfile --help
```

#### 2. Install with uv/pip

```bash
uv pip install linkfile-cli
```

## First Use

Initialize local config and the SQLite index:

```bash
linkfile setup
```

Add Cloudflare R2 or another S3-compatible storage backend:

```powershell
linkfile storage add s3 `
  --name linkfile-r2 `
  --endpoint-url https://<account-id>.r2.cloudflarestorage.com `
  --region auto `
  --bucket linkfile `
  --prefix uploads `
  --public-base-url https://files.example.com `
  --access-key-id <access-key-id> `
  --secret-access-key <secret-access-key>
```

Add Cloudreve:

```powershell
linkfile storage add cloudreve `
  --name cloudreve-test `
  --base-url https://pan.example.com `
  --username user@example.com `
  --password <password> `
  --root-path /LinkFile `
  --prefer-direct-url
```

Test a storage method:

```bash
linkfile storage test cloudreve-test
```

Upload a file:

```bash
linkfile upload test/test.jpg --storage cloudreve-test
```

The output includes a file ID:

```text
ID: file_xxx
File: test.jpg
Raw:
https://...
```

Download and delete by file ID:

```bash
linkfile download file_xxx
linkfile delete file_xxx --yes
```

## CLI Documentation

### `linkfile setup`

Creates the local config file and local SQLite index.

The config stores storage methods and credentials locally. In `0.1.1`, credentials are stored in plain text in `config.json`.

### `linkfile storage add s3`

Adds an S3-compatible storage method.

Common options:

- `--name`
- `--endpoint-url`
- `--region`
- `--bucket`
- `--prefix`
- `--public-base-url`
- `--path-style`
- `--access-key-id`
- `--secret-access-key`

Cloudflare R2 endpoints are automatically handled with path-style addressing and region `auto` for signed URLs.

### `linkfile storage add cloudreve`

Adds a Cloudreve v4 storage method.

Common options:

- `--name`
- `--base-url`
- `--username`
- `--password`
- `--root-path`
- `--prefer-direct-url`

Cloudreve direct links do not support LinkFile-side expiration. If `--expire` is used with Cloudreve direct links, the CLI warns that the option will be ignored.

### `linkfile storage test <name>`

Tests whether a configured storage method is reachable.

### `linkfile storage delete <name> --yes`

Deletes a storage method from the local config.

If the deleted storage method is the default, LinkFile automatically selects the first remaining storage method as the new default.

### `linkfile upload <path>`

Uploads a local file through a configured storage method.

Common options:

- `--storage`, `-s`
- `--expire`, `-e`
- `--format`, `-f`: `text` or `json`

Temporary URLs are generated on demand and are not stored in the local index.

### `linkfile list`

Lists local file records from the SQLite index.

### `linkfile info <file_id>`

Shows metadata for a local file record and generates a fresh temporary URL when supported.

### `linkfile download <file_id> [destination]`

Downloads a file by local file ID.

If `destination` is omitted, the file is downloaded to the current directory.

### `linkfile delete <file_id> --yes`

Deletes the remote file when supported and removes the local index record.

Use `--local-only` to remove only the local index record.

## TODO

- `v0.2`: API basics, including login authentication, API tokens, file metadata APIs, storage method APIs, share APIs, and local-server storage.
- `v0.3`: Web basics, including login, file list, web upload, public share pages, raw links, and token management.
- `v0.4`: Encryption, including server-managed encrypted storage configs, E2EE storage configs, master key import/export, re-encryption, and server key rotation.
- `v0.5`: Device sync, including CLI device keys, approved devices, and wrapped user data keys.
- `v0.6`: CLI and Web sync, including push/pull, storage method sync, file index sync, and conflict handling.
- `v0.7`: Full Web management, including storage editing, token scopes, share passwords, download limits, download logs, previews, thumbnails, and batch actions.
- `v0.8`: Ecosystem expansion, including a fuller Python SDK, async SDK, WebDAV, OneDrive, Google Drive, TUI, 2FA, admin tools, and quotas.

## License

MIT
