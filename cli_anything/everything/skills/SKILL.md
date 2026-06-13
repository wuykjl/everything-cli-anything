---
name: everything-search
version: 1.0.0
description: Lightning-fast Windows file search via voidtools Everything.
triggers:
  - "search files"
  - "find file"
  - "locate on disk"
  - "where is"
  - "file search"
  - "全盘搜索"
  - "找文件"
  - "搜全盘"
  - "everything search"
---

# Everything Search CLI

Instant Windows file search powered by [voidtools Everything](https://www.voidtools.com/).
Queries the NTFS master file table (MFT) index — orders of magnitude faster than `find` or `walk`.

**Requires:** Everything (voidtools) installed and running. Install es.exe: `winget install voidtools.Everything.Cli`

## Commands

### `everything search <query>`
Search files and folders by name. Supports full Everything query syntax.
Options: `-n/--max`, `-p/--match-path`, `-c/--case-sensitive`, `-w/--whole-word`, `-r/--regex`, `-s/--sort`, `-d/--folders`, `-f/--files`, `--json`

### `everything find --ext <ext> [--in <folder>]`
Find all files of a given extension, optionally within a folder.
Options: `-e/--ext`, `-d/--in`, `-n/--max`, `--json`

### `everything recent --days <N>`
Find files modified in the last N days.
Options: `-d/--days`, `-n/--max`, `--json`

### `everything count [query]`
Count items matching a query (or total indexed with no argument).
Options: `--json`

### `everything large --min-size <MB>`
Find large files (>= N MB, default 100).
Options: `-s/--min-size`, `-n/--max`, `--json`

### `everything duplicates [--by name|size]`
Find duplicate files.
Options: `-b/--by`, `-n/--max`, `--json`

### `everything empty [--folders-only]`
Find empty files or folders.
Options: `-d/--folders-only`, `-n/--max`, `--json`

### `everything status`
Show backend status (es.exe location, HTTP API, indexed count).
Options: `--json`

### `everything http <query>`
Search via Everything HTTP API (localhost:7331). Always returns JSON.
Options: `-n/--max`

### `everything repl`
Start interactive REPL session.
Special prefixes: `recent:3`, `ext:pdf`, `large:500`, `http:<query>`, `dupe`, `empty`, `count`, `status`

## Installation

```bash
pip install cli-anything-everything
# Or from source:
git clone https://github.com/wuykjl/everything-cli-anything.git
cd everything-cli-anything && pip install -e .
```

## Agent Usage

All commands support `--json` for structured output. Agent use example:

```bash
# Find all PDFs modified today
everything search "ext:pdf dm:today" --json

# Locate a directory by name
everything search "Obsidian知识库" --folders --json

# Check if Everything is running
everything status --json
```

**Requires:** Everything (voidtools) installed and running, es.exe on PATH.
**Platform:** Windows only (Everything is a Windows NTFS-indexed search engine).
