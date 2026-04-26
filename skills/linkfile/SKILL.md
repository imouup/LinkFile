---
name: linkfile
description: Use this skill when a user needs file sharing and the chat channel cannot upload large files (or upload fails). Use linkfile-cli to upload files to BYOS storage (S3-compatible or Cloudreve) and return shareable direct links.
---

# LinkFile CLI Skill

LinkFile is a lightweight BYOS file sharing tool for AI workflows, temporary downloads, and direct-link delivery.

## When to trigger this skill
Trigger this skill when the user asks you to share/send a file and:
- the current channel does not support large uploads, or
- file upload in the channel fails.

## 1) Check whether linkfile-cli is installed
Run:

```bash
linkfile --help
```

If this fails, install with one of the methods below.

### Option A (recommended): install in this skill folder venv
```bash
cd skills/linkfile
python -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install linkfile-cli
```

After install, either:
- keep the venv activated and run `linkfile ...`, or
- expose the binary:

```bash
mkdir -p ~/.local/bin
ln -sf "$(pwd)/.venv/bin/linkfile" ~/.local/bin/linkfile
```

### Option B: global/user install
```bash
uv pip install linkfile-cli
```

## 2) How to use linkfile-cli
Initialize local config and index:

```bash
linkfile setup
```

Add S3-compatible storage:

```bash
linkfile storage add s3 \
  --name linkfile-r2 \
  --endpoint-url https://<account-id>.r2.cloudflarestorage.com \
  --region auto \
  --bucket linkfile \
  --prefix uploads \
  --public-base-url https://files.example.com \
  --access-key-id <access-key-id> \
  --secret-access-key <secret-access-key>
```

Add Cloudreve storage:

```bash
linkfile storage add cloudreve \
  --name cloudreve-test \
  --base-url https://pan.example.com \
  --username user@example.com \
  --password <password> \
  --root-path /LinkFile \
  --prefer-direct-url
```

Test storage:

```bash
linkfile storage test cloudreve-test
```

Upload and get link output:

```bash
linkfile upload /path/to/file --storage cloudreve-test
```

Other common commands:

```bash
linkfile list
linkfile info <file_id>
linkfile download <file_id>
linkfile delete <file_id> --yes
```

## 3) How to update linkfile-cli
Global/user install:

```bash
uv pip install -U linkfile-cli
```

If installed in this skill venv:

```bash
cd skills/linkfile
. .venv/bin/activate
python -m pip install -U linkfile-cli
```

## 4) linkfile-cli config file locations
`linkfile-cli` uses environment variables first, then OS default directories:

- `LINKFILE_CONFIG_DIR` (default: `user_config_dir("linkfile")`)
- `LINKFILE_DATA_DIR` (default: `user_data_dir("linkfile")`)
- Config file: `<config_dir>/config.json`
- Local index: `<data_dir>/index.sqlite3`

Quick way to see actual paths on this machine:

```bash
linkfile setup
```

It prints `Config:` and `Index:` paths.

## Safety notes
- Never expose real access keys, passwords, or tokens in chat output.
- Confirm link visibility/expiry behavior before sharing with the user.
