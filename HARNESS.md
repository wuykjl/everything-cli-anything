# Everything Search CLI — Harness Methodology

## Software

**voidtools Everything** — Windows desktop search engine that indexes NTFS master file table (MFT) entries in real time. Provides instant filename search via a background service.

- **Website**: https://www.voidtools.com
- **CLI**: `es.exe` (IPC to Everything service)
- **API**: HTTP server on `localhost:7331` (optional)
- **Index**: NTFS MFT — updated in real time, no periodic scan
- **License**: Freeware (MIT for the CLI)

## Backend Architecture

Two transport modes:

| Mode | Mechanism | When to use |
|------|-----------|-------------|
| **es.exe subprocess** | `es.exe <query> -n <count>` | Default — always available when Everything is running |
| **HTTP API** | `GET localhost:7331/?s=<query>&j=1` | Structured JSON response, requires explicit server enable |

Both wrap the same index. The HTTP API returns structured JSON natively; es.exe requires text parsing.

## Command Design

The CLI follows the standard CLI-Anything convention:

- **`search`** — primary entry point, full Everything query syntax
- **`find`** — convenience for extension-based lookups
- **`recent`** — date-filtered results
- **`count`** — aggregate statistics
- **`large`** — size-filtered (convenience over raw `size:>Nmb` syntax)
- **`duplicates`** — dedup by name or size
- **`empty`** — zero-length files or empty folders
- **`status`** — diagnostic info for debugging
- **`http`** — direct HTTP API access
- **`repl`** — interactive session with prefix shortcuts

Every command supports `--json` for structured, agent-consumable output.

## State Model

Everything is stateless at the query level — each search is independent.
The REPL maintains a session context for convenience but doesn't cache results.

## Security

- Subprocess calls use explicit path resolution (no shell injection)
- HTTP requests are localhost-only (`127.0.0.1:7331`)
- No write operations exposed — Everything CLI is read-only by design

## Platform

**Windows only.** Everything relies on NTFS MFT indexing, a Windows-specific filesystem feature.

## Testing

```bash
cd everything-cli-anything
pip install -e ".[dev]"

# Unit tests (always runnable)
pytest cli_anything/everything/tests/ -v -m "not integration"

# Integration tests (require Everything running)
pytest cli_anything/everything/tests/ -v
```

## Known Limitations

1. **Windows only** — no macOS/Linux equivalent exists (Everything is NTFS-only)
2. **GUI dependency** — the Everything GUI app must be running for es.exe to work (IPC requirement)
3. **HTTP API latency** — HTTP mode adds ~1-2ms overhead vs direct es.exe
4. **Chinese character encoding** — HTTP API queries with CJK characters must be URL-encoded
