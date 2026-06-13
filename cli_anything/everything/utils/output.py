"""Console output formatters for Everything Search CLI."""


def format_results(results) -> str:
    """Format SearchResults as human-readable table."""
    total = results.total
    q = results.query
    t = results.time_ms
    lines = [f"{total} results for '{q}' ({t}ms)", "-" * 60]
    for it in results.items:
        lines.append(it.full_path)
    if not results.items:
        lines.append("(no results)")
    return "\n".join(lines)


def format_status(info: dict) -> str:
    """Format backend status as key-value text."""
    lines = [
        "Everything Search Status",
        "-" * 40,
        f"  es.exe:     {'found' if info['available'] else 'MISSING'} ({info.get('es_path', 'n/a')})",
        f"  HTTP API:   {'UP' if info.get('http_api') else 'DOWN'}",
        f"  Indexed:    {info.get('total_indexed', '?')} items",
    ]
    return "\n".join(lines)
