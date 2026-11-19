"""Human-friendly terminal commands. Nothing is removed without --apply."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape
from rich.prompt import Confirm, Prompt
from rich.table import Table

from . import __version__
from .config import Settings
from .duplicates import find_duplicates
from .models import CleanSlateError
from .rules import RULES
from .scanner import scan
from .service import CleanupService

app = typer.Typer(help="Inspect, clean, and restore developer workspaces safely.", no_args_is_help=True)
console = Console()


def _version(value: bool) -> None:
    if value:
        console.print(f"Clean Slate {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[bool, typer.Option("--version", callback=_version,
                                          is_eager=True, help="Show version")] = False,
) -> None:
    """Clean Slate never permanently deletes files: cleanup moves items to quarantine."""


def _service(root: Path) -> CleanupService:
    return CleanupService(Settings.load(root.expanduser().absolute()).data_dir)


def _format_bytes(number: int) -> str:
    size = float(number)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:,.1f} {unit}" if unit != "B" else f"{number:,} B"
        size /= 1024
    return f"{number:,} B"


def _print_candidates(result) -> None:
    console.print(f"\n[bold]Workspace:[/bold] {escape(result.root)}")
    console.print(f"Projects: {len(result.projects)}   Candidates: {len(result.candidates)}")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim")
    table.add_column("Category")
    table.add_column("Risk")
    table.add_column("Size", justify="right")
    table.add_column("Path", overflow="fold")
    for c in result.candidates:
        risk = "PROTECTED" if not c.can_clean else c.risk.upper()
        table.add_row(c.id[:8], c.category, risk, _format_bytes(c.bytes), escape(c.path))
    console.print(table)
    console.print(f"Potentially cleanable: [bold]{_format_bytes(result.to_dict()['total_bytes'])}[/bold]")
    if result.warnings:
        for warning in result.warnings:
            console.print(f"[yellow]Warning:[/yellow] {escape(warning)}")


@app.command("scan")
def scan_workspace(
    path: Annotated[Path, typer.Argument(help="Directory containing your projects")] = Path.cwd(),
    json_output: Annotated[bool, typer.Option("--json", help="Machine-readable scan report")] = False,
    max_depth: Annotated[int, typer.Option(min=0, max=30)] = 8,
) -> None:
    """Read-only scan of projects and cleanup opportunities."""
    try:
        result = scan(path, max_depth=max_depth)
        if json_output:
            console.print_json(json.dumps(result.to_dict()))
        else:
            _print_candidates(result)
    except CleanSlateError as exc:
        _error(exc)


@app.command()
def projects(
    path: Annotated[Path, typer.Argument()] = Path.cwd(),
) -> None:
    """Discover supported project environments."""
    try:
        result = scan(path)
        table = Table("Project", "Ecosystem", "Git")
        for item in result.projects:
            table.add_row(escape(item.path), ", ".join(item.ecosystems), "yes" if item.git_repository else "no")
        console.print(table)
    except CleanSlateError as exc:
        _error(exc)


@app.command()
def clean(
    path: Annotated[Path, typer.Argument(help="Workspace path")] = Path.cwd(),
    apply: Annotated[bool, typer.Option("--apply", help="Move selected items to quarantine")] = False,
    include_review: Annotated[bool, typer.Option("--include-review", help="Include higher-risk items")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip interactive confirmation")] = False,
) -> None:
    """Preview safe candidates by default. Requires --apply to change anything."""
    try:
        result = scan(path)
        selected = [
            item for item in result.candidates
            if item.can_clean and (item.risk == "safe" or include_review)
        ]
        _print_candidates(result)
        console.print(f"\nSelected: {len(selected)} items; {_format_bytes(sum(c.bytes for c in selected))}")
        if not selected:
            console.print("No eligible items found.")
            return
        if not apply:
            console.print("[green]Dry run only.[/green] Add --apply to move files to quarantine.")
            return
        review_count = sum(item.risk == "review" for item in selected)
        if review_count and not yes:
            console.print(f"[yellow]{review_count} review-risk item(s) selected.[/yellow]")
            if Prompt.ask("Type REVIEW to approve these items") != "REVIEW":
                console.print("Cancelled.")
                return
        if not yes and not Confirm.ask("Proceed with moving selected items to quarantine?", default=False):
            console.print("Cancelled.")
            return
        response = _service(path).cleanup(result, [item.id for item in selected],
                                          confirm_review=include_review)
        operation = response["operation"]
        console.print(f"Operation: [bold]{operation['id']}[/bold] ({operation['status']})")
        console.print(f"Moved: {response['moved_count']} items ({_format_bytes(operation['bytes'])})")
        console.print(f"To restore: [cyan]cleanslate restore {operation['id']}[/cyan]")
        for error in response["errors"]:
            console.print(f"[red]{escape(error)}[/red]")
        if response["errors"]:
            raise typer.Exit(code=1)
    except CleanSlateError as exc:
        _error(exc)


@app.command()
def history(
    limit: Annotated[int, typer.Option(min=1, max=200)] = 30,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """List durable cleanup history (including recoverable items)."""
    operations = _service(Path.cwd()).journal.history(limit)
    if json_output:
        console.print_json(json.dumps(operations))
        return
    table = Table("Operation ID", "Time (UTC)", "State", "Items", "Size")
    for op in operations:
        table.add_row(op["id"], op["created_at"][:19], op["status"],
                      str(len(op["items"])), _format_bytes(op["bytes"]))
    console.print(table)


@app.command()
def restore(
    operation_id: Annotated[str, typer.Argument(help="Cleanup operation ID from history")],
    yes: Annotated[bool, typer.Option("--yes", "-y")] = False,
) -> None:
    """Restore all remaining items from an operation without overwriting files."""
    try:
        service = _service(Path.cwd())
        op = service.journal.operation(operation_id)
        console.print(f"Restore {len(op['items']) - op['restored_count']} item(s) in {escape(op['root'])}?")
        if not yes and not Confirm.ask("Continue?", default=False):
            return
        result = service.restore(operation_id)
        console.print(f"Restored: {result['restored_count']} item(s)")
        for error in result["errors"]:
            console.print(f"[red]{escape(error)}[/red]")
        if result["errors"]:
            raise typer.Exit(code=1)
    except CleanSlateError as exc:
        _error(exc)


@app.command()
def duplicates(
    path: Annotated[Path, typer.Argument()] = Path.cwd(),
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Find byte-for-byte duplicates; read-only and bounded by default."""
    try:
        result = find_duplicates(path)
        if json_output:
            console.print_json(json.dumps(result))
            return
        console.print(f"Scanned: {result['files_scanned']:,} files")
        console.print(f"Duplicate space: [bold]{_format_bytes(result['reclaimable_bytes'])}[/bold]")
        for group in result["groups"]:
            console.print(f"\n[cyan]{_format_bytes(group['reclaimable_bytes'])}[/cyan] potential")
            for path in group["paths"]:
                console.print(f"  {escape(path)}")
        console.print("[dim]Read-only; Clean Slate never removes duplicates automatically.[/dim]")
    except CleanSlateError as exc:
        _error(exc)


@app.command()
def rules() -> None:
    """Explain the built-in cleanup policy."""
    table = Table("Rule ID", "Risk", "Applies to", "Reason")
    for rule in RULES:
        table.add_row(rule.id, rule.risk, ", ".join(sorted(rule.ecosystems)), rule.explanation)
    console.print(table)


@app.command()
def web(port: Annotated[int, typer.Option(min=1024, max=65535)] = 8765) -> None:
    """Start the dashboard/API on loopback only; never exposes user files remotely."""
    try:
        import uvicorn
    except ImportError:
        console.print("Install the web extra first: pip install -e '.[web]'")
        raise typer.Exit(code=1) from None
    console.print(f"Local dashboard: [cyan]http://127.0.0.1:{port}[/cyan]")
    uvicorn.run("cleanslate.api:create_app", factory=True, host="127.0.0.1", port=port)


def _error(exc: CleanSlateError) -> None:
    console.print(f"[red]Error:[/red] {escape(str(exc))}")
    raise typer.Exit(code=1) from exc
