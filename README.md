# Everything Search CLI

> Lightning-fast Windows file search for AI agents — powered by voidtools Everything.

`everything` gives AI agents and developers instant file search on Windows via
[voidtools Everything](https://www.voidtools.com/)'s NTFS master file table index.
Orders of magnitude faster than `find`, `locate`, or filesystem walk.

## Why

Everything indexes your entire filesystem in seconds and answers queries in **milliseconds**.
But its power is locked behind a GUI — until now. This CLI harness wraps `es.exe` and the
Everything HTTP API into structured, agent-consumable output.

- **~300x faster** than `os.walk()` (220ms vs 66,000ms benchmark)
- **JSON output** for AI agent consumption (`--json`)
- **Full query syntax**: `ext:pdf dm:today`, `size:>100mb`, regex, folder-only
- **No admin rights needed** — Everything runs as a standard user service

## Install

### Prerequisites

1. Install [Everything](https://www.voidtools.com/downloads/) (the GUI app — it runs the background service)
2. Install the CLI tool: `winget install voidtools.Everything.Cli`
3. Start Everything (tray icon — keep it running)

### Install this harness

```bash
pip install cli-anything-everything

# Or from source:
git clone https://github.com/wuykjl/everything-cli-anything.git
cd everything-cli-anything && pip install -e .
```

## Quick start

```bash
# Search by name
everything search "budget"

# Find all PDFs modified today
everything search "ext:pdf dm:today"

# Find large files (>500MB)
everything large --min-size 500

# Recent files (last 3 days)
everything recent --days 3

# JSON output for AI agents
everything search "report" --json
everything status --json

# Interactive REPL
everything repl
```

## Commands

| Command | Description |
|---------|-------------|
| `search <query>` | Search files by name |
| `find --ext <ext>` | Find by extension |
| `recent --days <n>` | Recent files |
| `count [query]` | Count matching items |
| `large --min-size <mb>` | Large files |
| `duplicates` | Find duplicates |
| `empty` | Empty files/folders |
| `status` | Backend diagnostics |
| `http <query>` | HTTP API search |
| `repl` | Interactive session |

All commands support `--json` for structured output.

## Agent integration

Install the skill definition:

```bash
npx skills add wuykjl/everything-cli-anything -g -y
```

Or via CLI-Hub (once merged to registry):

```bash
cli-hub search everything
cli-hub install everything
```

## Known limitations

- **Windows only** — Everything is a Windows NTFS search engine
- **GUI app must be running** — `es.exe` communicates with it via IPC
- **HTTP API is optional** — enabled via Tools → Options → HTTP Server
- **Chinese encoding** — use URL encoding when querying via HTTP API with Chinese characters

## How it works

```
AI Agent
    │
    ▼
everything --json search "query"
    │
    ▼
es.exe (subprocess)  or  HTTP localhost:7331
    │
    ▼
Everything Service (IPC / Named Pipes)
    │
    ▼
NTFS MFT Index → instant results
```

## License

MIT
