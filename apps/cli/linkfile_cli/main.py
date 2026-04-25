from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from linkfile_core.config import (
    ensure_local_environment,
    find_storage_method,
    get_default_paths,
    load_config,
    remove_storage_method,
    save_config,
    upsert_storage_method,
)
from linkfile_core.index import FileRecord, LocalIndex
from linkfile_core.models import UploadResult
from rich.console import Console
from rich.table import Table
from storage import create_strategy

app = typer.Typer(help="LinkFile offline-first BYOS file sharing CLI.")
storage_app = typer.Typer(help="Manage storage backends.")
app.add_typer(storage_app, name="storage")
console = Console()


@app.command()
def setup() -> None:
    """Create the local LinkFile configuration and data directories."""
    paths = get_default_paths()
    if paths.config_file.exists() and paths.index_file.exists():
        if typer.confirm(
            "Config and index already exist. Reset and back up the folders?",
            default=False,
        ):
            _backup_existing_paths(paths)
        else:
            console.print(f"Config: {paths.config_file}")
            console.print(f"Index:  {paths.index_file}")
            return
    paths = ensure_local_environment(paths)
    LocalIndex(paths.index_file).initialize()

    console.print(f"Config: {paths.config_file}")
    console.print(f"Index:  {paths.index_file}")


@storage_app.command("add")
def storage_add(
    storage_type: Annotated[str, typer.Argument(help="s3 or cloudreve")],
    name: Annotated[str | None, typer.Option("--name")] = None,
    endpoint_url: Annotated[str | None, typer.Option("--endpoint-url")] = None,
    region: Annotated[str | None, typer.Option("--region")] = None,
    bucket: Annotated[str | None, typer.Option("--bucket")] = None,
    prefix: Annotated[str, typer.Option("--prefix")] = "",
    public_base_url: Annotated[str | None, typer.Option("--public-base-url")] = None,
    use_path_style: Annotated[bool, typer.Option("--path-style/--virtual-hosted")] = False,
    access_key_id: Annotated[str | None, typer.Option("--access-key-id")] = None,
    secret_access_key: Annotated[str | None, typer.Option("--secret-access-key")] = None,
    base_url: Annotated[str | None, typer.Option("--base-url")] = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    password: Annotated[str | None, typer.Option("--password")] = None,
    root_path: Annotated[str, typer.Option("--root-path")] = "/LinkFile",
    prefer_direct_url: Annotated[bool, typer.Option("--prefer-direct-url")] = True,
) -> None:
    """Start an interactive storage backend setup flow."""
    ensure_local_environment()
    config = load_config()
    if storage_type == "s3":
        method = _build_s3_method(
            name=name,
            endpoint_url=endpoint_url,
            region=region,
            bucket=bucket,
            prefix=prefix,
            public_base_url=public_base_url,
            use_path_style=use_path_style,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        )
    elif storage_type == "cloudreve":
        method = _build_cloudreve_method(
            name=name,
            base_url=base_url,
            username=username,
            password=password,
            root_path=root_path,
            prefer_direct_url=prefer_direct_url,
        )
    else:
        raise typer.BadParameter("storage_type must be either 's3' or 'cloudreve'.")

    upsert_storage_method(config, method)
    save_config(config)
    console.print(f"Storage method saved: [bold]{method['name']}[/bold] ({method['id']})")


@storage_app.command("test")
def storage_test(name: str) -> None:
    """Test a configured storage backend."""
    method = find_storage_method(load_config(), name)
    create_strategy(method).test_connection()
    console.print(f"Storage method is available: [bold]{method['name']}[/bold]")


@storage_app.command("delete")
def storage_delete(
    name: Annotated[str, typer.Argument(help="Storage method name or id")],
    yes: Annotated[bool, typer.Option("--yes", "-y")] = False,
) -> None:
    """Delete a configured storage backend."""
    config = load_config()
    method = find_storage_method(config, name)
    if not yes:
        typer.confirm(f"Delete storage method {method['name']}?", abort=True)
    remove_storage_method(config, name)
    save_config(config)
    console.print(f"Storage method deleted: [bold]{method['name']}[/bold]")


@app.command()
def upload(
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    storage: Annotated[str | None, typer.Option("--storage", "-s")] = None,
    expire: Annotated[str | None, typer.Option("--expire", "-e")] = None,
    output_format: Annotated[str, typer.Option("--format", "-f")] = "text",
) -> None:
    """Upload a file through the selected storage backend."""
    ensure_local_environment()
    method = find_storage_method(load_config(), storage)
    if method.get("type") == "cloudreve" and expire:
        console.print("Cloudreve direct links do not support expiration; --expire will be ignored.")
        typer.confirm("Continue?", abort=True)
    try:
        result = create_strategy(method).upload_file(file, expire=expire)
    except RuntimeError as exc:
        console.print(f"[red]Upload failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    LocalIndex().add_upload_result(result)
    _print_upload_result(result, output_format)


# @app.command()
# def serve(
#     file: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
#     expire: Annotated[str, typer.Option("--expire", "-e")] = "10m",
#     qr: Annotated[bool, typer.Option("--qr")] = False,
# ) -> None:
#     """Start a temporary local-server share for a file."""
#     console.print(f"Serving: {file}")
#     console.print(f"Expires: {expire}")
#     console.print(f"QR: {'enabled' if qr else 'disabled'}")


@app.command("list")
def list_files() -> None:
    """List local file index records."""
    records = LocalIndex().list_files()
    if not records:
        console.print("No local file records.")
        return
    table = Table("ID", "Name", "Size", "Storage", "Key")
    for record in records:
        table.add_row(
            record.file_id,
            record.name,
            str(record.size),
            record.storage_method_id,
            record.storage_key,
        )
    console.print(table)


@app.command()
def info(file_id: str | None = None) -> None:
    """Show local configuration or file metadata."""
    if not file_id:
        console.print_json(json.dumps(load_config()))
        return
    record = LocalIndex().get_file(file_id)
    method = find_storage_method(load_config(), record.storage_method_id)
    fresh_url = create_strategy(method).generate_temporary_url(record)
    payload = _record_payload(record)
    if fresh_url:
        payload["temporary_url"] = fresh_url
    console.print_json(json.dumps(payload))


@app.command()
def download(
    file_id: str,
    destination: Annotated[
        Path,
        typer.Argument(help="Destination path or directory.", show_default=False),
    ] = Path("."),
) -> None:
    """Download a file by LinkFile id."""
    record = LocalIndex().get_file(file_id)
    method = find_storage_method(load_config(), record.storage_method_id)
    try:
        target = create_strategy(method).download_file(record, destination)
    except RuntimeError as exc:
        console.print(f"[red]Download failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"Downloaded: {target}")


@app.command()
def delete(
    file_id: str,
    local_only: Annotated[bool, typer.Option("--local-only")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y")] = False,
) -> None:
    """Delete a file record and, when supported, the remote object."""
    record = LocalIndex().get_file(file_id)
    if not yes:
        typer.confirm(f"Delete {record.name}?", abort=True)
    if not local_only:
        method = find_storage_method(load_config(), record.storage_method_id)
        try:
            create_strategy(method).delete_file(record)
        except RuntimeError as exc:
            console.print(f"[red]Delete failed:[/red] {exc}")
            raise typer.Exit(1) from exc
    LocalIndex().delete_file(file_id)
    console.print(f"Deleted: {file_id}")


def _build_s3_method(
    *,
    name: str | None,
    endpoint_url: str | None,
    region: str | None,
    bucket: str | None,
    prefix: str,
    public_base_url: str | None,
    use_path_style: bool,
    access_key_id: str | None,
    secret_access_key: str | None,
) -> dict[str, object]:
    name = name or typer.prompt("Storage name")
    return {
        "id": _method_id(name),
        "name": name,
        "type": "s3",
        "endpoint_url": endpoint_url or typer.prompt("Endpoint URL", default=""),
        "region": region or typer.prompt("Region", default="auto"),
        "bucket": bucket or typer.prompt("Bucket"),
        "prefix": prefix,
        "public_base_url": public_base_url or typer.prompt("Public base URL", default=""),
        "use_path_style": use_path_style,
        "access_key_id": access_key_id or typer.prompt("Access key ID"),
        "secret_access_key": secret_access_key
        or typer.prompt("Secret access key", hide_input=True),
    }


def _build_cloudreve_method(
    *,
    name: str | None,
    base_url: str | None,
    username: str | None,
    password: str | None,
    root_path: str,
    prefer_direct_url: bool,
) -> dict[str, object]:
    name = name or typer.prompt("Storage name")
    return {
        "id": _method_id(name),
        "name": name,
        "type": "cloudreve",
        "base_url": base_url or typer.prompt("Cloudreve base URL"),
        "username": username or typer.prompt("Username"),
        "password": password or typer.prompt("Password", hide_input=True),
        "root_path": root_path,
        "prefer_direct_url": prefer_direct_url,
    }


def _method_id(name: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
    slug = "-".join(part for part in slug.split("-") if part)
    return slug or f"storage-{uuid4().hex[:8]}"


def _backup_existing_paths(paths) -> None:
    backed_up: set[Path] = set()
    for directory in (paths.config_dir, paths.data_dir):
        if directory in backed_up or not directory.exists():
            continue
        backup_path = _next_backup_path(directory)
        directory.rename(backup_path)
        backed_up.add(directory)
        console.print(f"Backed up: {directory} -> {backup_path}")


def _next_backup_path(directory: Path) -> Path:
    suffix = "bak"
    candidate = directory.with_name(f"{directory.name}{suffix}")
    if not candidate.exists():
        return candidate
    index = 1
    while True:
        candidate = directory.with_name(f"{directory.name}{suffix}{index}")
        if not candidate.exists():
            return candidate
        index += 1


def _print_upload_result(result: UploadResult, output_format: str) -> None:
    payload = result.model_dump(mode="json")
    if output_format == "json":
        console.print_json(json.dumps(payload))
        return
    if output_format != "text":
        raise typer.BadParameter("--format currently supports: text, json")
    console.print(f"ID: {result.file_id}")
    console.print(f"File: {result.name}")
    if result.share_url:
        console.print("Share:")
        console.print(result.share_url, soft_wrap=True)
    if result.raw_url:
        console.print("Raw:")
        console.print(result.raw_url, soft_wrap=True)
    if result.public_url:
        console.print("Public:")
        console.print(result.public_url, soft_wrap=True)
        if str(result.storage_type) == "s3":
            console.print("Note: Public URL is long-lived.")
    if result.expires_at and str(result.storage_type) != "cloudreve":
        console.print(f"Expire: {result.expires_at.isoformat()}")


def _record_payload(record: FileRecord) -> dict[str, object]:
    return {
        "file_id": record.file_id,
        "name": record.name,
        "size": record.size,
        "mime_type": record.mime_type,
        "storage_method_id": record.storage_method_id,
        "storage_type": record.storage_type,
        "storage_key": record.storage_key,
        "public_url": record.public_url,
        "share_url": record.share_url,
        "expires_at": record.expires_at,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "metadata": record.metadata,
    }
