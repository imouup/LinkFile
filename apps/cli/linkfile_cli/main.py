from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from linkfile_core.config import get_default_paths

app = typer.Typer(help="LinkFile offline-first BYOS file sharing CLI.")
storage_app = typer.Typer(help="Manage storage backends.")
app.add_typer(storage_app, name="storage")
console = Console()


@app.command()
def setup() -> None:
    """Create the local LinkFile configuration and data directories."""
    paths = get_default_paths()
    paths.config_dir.mkdir(parents=True, exist_ok=True)
    paths.data_dir.mkdir(parents=True, exist_ok=True)

    if not paths.config_file.exists():
        paths.config_file.write_text(
            json.dumps(
                {
                    "version": 1,
                    "mode": "local_only",
                    "server": {"enabled": False, "url": "https://api.linkfile.app"},
                    "storage_methods": [],
                    "defaults": {"storage_method_id": None},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    console.print(f"Config: {paths.config_file}")
    console.print(f"Index:  {paths.index_file}")


@storage_app.command("add")
def storage_add(storage_type: Annotated[str, typer.Argument(help="s3, cloudreve, or local-server")]) -> None:
    """Start an interactive storage backend setup flow."""
    console.print(
        f"Storage setup for [bold]{storage_type}[/bold] is reserved for the v0.1 implementation."
    )


@storage_app.command("test")
def storage_test(name: str) -> None:
    """Test a configured storage backend."""
    console.print(f"Storage test for [bold]{name}[/bold] is reserved for the v0.1 implementation.")


@app.command()
def upload(
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    storage: Annotated[str | None, typer.Option("--storage", "-s")] = None,
    expire: Annotated[str | None, typer.Option("--expire", "-e")] = None,
) -> None:
    """Upload a file through the selected storage backend."""
    console.print(f"Upload queued: {file}")
    console.print(f"Storage: {storage or 'default'}")
    console.print(f"Expire: {expire or 'storage default'}")


@app.command()
def serve(
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    expire: Annotated[str, typer.Option("--expire", "-e")] = "10m",
    qr: Annotated[bool, typer.Option("--qr")] = False,
) -> None:
    """Start a temporary local-server share for a file."""
    console.print(f"Serving: {file}")
    console.print(f"Expires: {expire}")
    console.print(f"QR: {'enabled' if qr else 'disabled'}")


@app.command("list")
def list_files() -> None:
    """List local file index records."""
    console.print("Local index listing is reserved for the v0.1 implementation.")


@app.command()
def info(file_id: str | None = None) -> None:
    """Show local configuration or file metadata."""
    console.print(f"Info target: {file_id or 'local configuration'}")


@app.command()
def download(file_id: str, destination: Path) -> None:
    """Download a file by LinkFile id."""
    console.print(f"Download {file_id} to {destination}")


@app.command()
def delete(file_id: str) -> None:
    """Delete a file record and, when supported, the remote object."""
    console.print(f"Delete requested: {file_id}")
