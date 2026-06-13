"""Everything Search CLI — lightning-fast Windows file search for AI agents.

Requires Everything (voidtools) installed and running.
Install CLI: pip install cli-anything-everything
Usage:
  everything search "my file" --json
  everything recent --days 3
  everything find --ext pdf --in "C:/Documents"
  everything status
  everything repl
"""

import json
import sys
from pathlib import Path
from typing import Optional

import click

from cli_anything.everything.core.backend import EverythingBackend, SearchResults
from cli_anything.everything.utils.output import format_results, format_status


_backend: Optional[EverythingBackend] = None


def get_backend() -> EverythingBackend:
    global _backend
    if _backend is None:
        _backend = EverythingBackend()
    return _backend


def _json_output(obj, compact: bool = False) -> None:
    """Print object as JSON to stdout."""
    indent = None if compact else 2
    click.echo(json.dumps(obj, indent=indent, ensure_ascii=False, default=str))


# ── CLI group ──────────────────────────────────────────────────────────────

@click.group()
@click.version_option(version="1.0.0", prog_name="everything")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Everything Search CLI — instant Windows file search for AI agents.

    Powered by voidtools Everything (NTFS MFT index).
    Requires Everything (voidtools) installed and running.
    """
    ctx.ensure_object(dict)


# ── search ────────────────────────────────────────────────────────────────

@main.command("search")
@click.argument("query")
@click.option("-n", "--max", type=int, default=50, help="Maximum results (default 50).")
@click.option("-p", "--match-path", is_flag=True, help="Match full path, not just filename.")
@click.option("-c", "--case-sensitive", is_flag=True, help="Case-sensitive search.")
@click.option("-w", "--whole-word", is_flag=True, help="Whole-word match.")
@click.option("-r", "--regex", is_flag=True, help="Use regex pattern.")
@click.option("-s", "--sort", "sort_by", type=click.Choice(["name", "path", "size", "date-modified", "extension"]), default="name", help="Sort field.")
@click.option("-d", "--folders", is_flag=True, help="Only return folders.")
@click.option("-f", "--files", is_flag=True, help="Only return files (not folders).")
@click.option("--json", "json_flag", is_flag=True, help="Output as JSON (for agent consumption).")
@click.option("--compact", is_flag=True, help="Compact JSON output.")
def cmd_search(
    query, max, match_path, case_sensitive, whole_word, regex, sort_by,
    folders, files, json_flag, compact,
) -> None:
    """Search files and folders by name.

    \b
    Examples:
      everything search "report"
      everything search "ext:pdf dm:today"
      everything search "budget" --folders --json
    """
    backend = get_backend()
    if not backend.available:
        click.echo("ERROR: es.exe not found. Install: winget install voidtools.Everything.Cli", err=True)
        sys.exit(1)

    results = backend.search(
        query=query,
        max_results=max,
        folders_only=folders,
        files_only=files,
    )

    if json_flag:
        obj = {
            "query": results.query,
            "total": results.total,
            "returned": results.returned,
            "time_ms": results.time_ms,
            "results": [
                {"name": it.name, "path": it.full_path, "extension": it.extension}
                for it in results.items
            ],
        }
        _json_output(obj, compact)
    else:
        click.echo(format_results(results))


# ── find ──────────────────────────────────────────────────────────────────

@main.command("find")
@click.option("-e", "--ext", "extension", help="Filter by extension (e.g. pdf, docx).")
@click.option("-d", "--in", "folder", help="Limit to folder path.")
@click.option("-n", "--max", type=int, default=100, help="Maximum results (default 100).")
@click.option("--json", "json_flag", is_flag=True, help="JSON output.")
def cmd_find(extension, folder, max, json_flag) -> None:
    """Find files by extension, optionally within a folder.

    \b
    Examples:
      everything find --ext pdf
      everything find --ext docx --in "C:/Users/wuyu/Downloads"
    """
    backend = get_backend()
    if not backend.available:
        click.echo("ERROR: es.exe not found.", err=True)
        sys.exit(1)

    if extension:
        results = backend.list_by_extension(extension, max_results=max, folder=folder)
    elif folder:
        results = backend.search(f'"{folder}"', max_results=max)
    else:
        click.echo("Specify --ext or --in to search.", err=True)
        sys.exit(1)

    if json_flag:
        _json_output({"query": results.query, "total": results.total, "items": [i.full_path for i in results.items]})
    else:
        click.echo(format_results(results))


# ── recent ────────────────────────────────────────────────────────────────

@main.command("recent")
@click.option("-d", "--days", type=int, default=1, help="Days back (default 1).")
@click.option("-n", "--max", type=int, default=50, help="Maximum results.")
@click.option("--json", "json_flag", is_flag=True, help="JSON output.")
def cmd_recent(days, max, json_flag) -> None:
    """Find recently modified files.

    \b
    Examples:
      everything recent --days 1
      everything recent --days 7 --json
    """
    backend = get_backend()
    if not backend.available:
        click.echo("ERROR: es.exe not found.", err=True)
        sys.exit(1)

    results = backend.find_recent(days=days, max_results=max)
    if json_flag:
        _json_output({"query": results.query, "total": results.total, "items": [i.full_path for i in results.items]})
    else:
        click.echo(format_results(results))


# ── count ─────────────────────────────────────────────────────────────────

@main.command("count")
@click.argument("query", default="")
@click.option("--json", "json_flag", is_flag=True, help="JSON output.")
def cmd_count(query, json_flag) -> None:
    """Count items matching query (no query = total indexed)."""
    backend = get_backend()
    if not backend.available:
        click.echo("ERROR: es.exe not found.", err=True)
        sys.exit(1)

    total = backend.count(query)
    if json_flag:
        _json_output({"query": query or "*", "count": total})
    else:
        click.echo(f"{total} items")


# ── large ─────────────────────────────────────────────────────────────────

@main.command("large")
@click.option("-s", "--min-size", type=int, default=100, help="Minimum size in MB (default 100).")
@click.option("-n", "--max", type=int, default=50, help="Maximum results.")
@click.option("--json", "json_flag", is_flag=True, help="JSON output.")
def cmd_large(min_size, max, json_flag) -> None:
    """Find large files (>= N MB).

    \b
    Examples:
      everything large --min-size 500
      everything large --min-size 1000 --json
    """
    backend = get_backend()
    if not backend.available:
        click.echo("ERROR: es.exe not found.", err=True)
        sys.exit(1)

    results = backend.find_large(min_size_mb=min_size, max_results=max)
    if json_flag:
        _json_output({"query": results.query, "total": results.total, "items": [i.full_path for i in results.items]})
    else:
        click.echo(format_results(results))


# ── duplicates ────────────────────────────────────────────────────────────

@main.command("duplicates")
@click.option("-b", "--by", type=click.Choice(["name", "size"]), default="name", help="Dedup by name or size.")
@click.option("-n", "--max", type=int, default=100, help="Maximum results.")
@click.option("--json", "json_flag", is_flag=True, help="JSON output.")
def cmd_duplicates(by, max, json_flag) -> None:
    """Find duplicate files.

    \b
    Examples:
      everything duplicates --by name
      everything duplicates --by size --json
    """
    backend = get_backend()
    if not backend.available:
        click.echo("ERROR: es.exe not found.", err=True)
        sys.exit(1)

    results = backend.find_duplicates(by=by, max_results=max)
    if json_flag:
        _json_output({"query": results.query, "total": results.total, "items": [i.full_path for i in results.items]})
    else:
        click.echo(format_results(results))


# ── empty ─────────────────────────────────────────────────────────────────

@main.command("empty")
@click.option("-d", "--folders-only", is_flag=True, help="Only empty folders.")
@click.option("-n", "--max", type=int, default=100, help="Maximum results.")
@click.option("--json", "json_flag", is_flag=True, help="JSON output.")
def cmd_empty(folders_only, max, json_flag) -> None:
    """Find empty files or folders."""
    backend = get_backend()
    if not backend.available:
        click.echo("ERROR: es.exe not found.", err=True)
        sys.exit(1)

    results = backend.find_empty(folders_only=folders_only, max_results=max)
    if json_flag:
        _json_output({"query": results.query, "total": results.total, "items": [i.full_path for i in results.items]})
    else:
        click.echo(format_results(results))


# ── status ────────────────────────────────────────────────────────────────

@main.command("status")
@click.option("--json", "json_flag", is_flag=True, help="JSON output.")
def cmd_status(json_flag) -> None:
    """Show Everything backend status."""
    backend = get_backend()
    info = backend.status()
    if json_flag:
        _json_output(info)
    else:
        click.echo(format_status(info))


# ── http ──────────────────────────────────────────────────────────────────

@main.command("http")
@click.argument("query")
@click.option("-n", "--max", type=int, default=50, help="Maximum results.")
def cmd_http(query, max) -> None:
    """Search via Everything HTTP API (requires HTTP server enabled).

    Always returns JSON (structured output from HTTP API).
    Enable HTTP server: Tools → Options → HTTP Server → Enable.

    \b
    Example:
      everything http "ext:pdf dm:today"
    """
    backend = get_backend()
    try:
        results = backend.search_http(query, max_results=max)
    except ConnectionError as exc:
        click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)

    _json_output({
        "query": results.query,
        "total": results.total,
        "returned": results.returned,
        "time_ms": results.time_ms,
        "results": [
            {"name": it.name, "path": it.full_path, "size": it.size, "date": it.date_modified}
            for it in results.items
        ],
    })


# ── repl ──────────────────────────────────────────────────────────────────

@main.command("repl")
def cmd_repl() -> None:
    """Start interactive REPL session."""
    backend = get_backend()
    if not backend.available:
        click.echo("ERROR: es.exe not found.", err=True)
        sys.exit(1)

    click.echo("Everything Search REPL")
    click.echo("Type 'help' for commands, 'exit' to quit.")
    click.echo(f"Total indexed: {backend.count()} files")

    while True:
        try:
            line = input("\neverything> ").strip()
        except (EOFError, KeyboardInterrupt):
            click.echo("\nGoodbye.")
            break

        if not line:
            continue
        if line.lower() in ("exit", "quit", "q"):
            click.echo("Goodbye.")
            break
        if line.lower() == "help":
            click.echo("Commands: <query>, recent:<days>, ext:<ext>, large:<mb>, dupe, empty, count, status, http:<query>")
            continue
        if line.lower() == "status":
            click.echo(format_status(backend.status()))
            continue
        if line.lower() == "count":
            click.echo(f"{backend.count()} items indexed")
            continue

        # Parse special prefixes
        parts = line.split(":", 1)
        if len(parts) == 2:
            prefix, value = parts
            if prefix == "recent":
                results = backend.find_recent(days=int(value) if value.isdigit() else 1)
            elif prefix == "ext":
                results = backend.list_by_extension(value)
            elif prefix == "large":
                results = backend.find_large(min_size_mb=int(value) if value.isdigit() else 100)
            elif prefix == "http":
                try:
                    results = backend.search_http(value)
                except ConnectionError:
                    click.echo("HTTP API not available.", err=True)
                    continue
            else:
                results = backend.search(line)
        elif line == "dupe":
            results = backend.find_duplicates()
        elif line == "empty":
            results = backend.find_empty()
        else:
            results = backend.search(line)

        click.echo(format_results(results))


if __name__ == "__main__":
    main()
