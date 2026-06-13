"""Everything Search backend — wraps es.exe CLI + Everything HTTP API.

Requirements:
  - Everything (voidtools) installed and running
  - es.exe on PATH (default: winget install voidtools.Everything.Cli)
  - Optional: HTTP API server enabled (Tools → Options → HTTP Server)

Security:
  - All subprocess calls use a dedicated es_path (no shell injection)
  - HTTP requests are local-only (localhost:7331)
"""

import json
import subprocess
import urllib.parse
import urllib.request
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class EverythingResult:
    """Single search result from Everything."""
    name: str
    path: str
    full_path: str
    size: int = 0
    date_modified: str = ""
    extension: str = ""

    def __post_init__(self) -> None:
        if not self.extension and self.name:
            self.extension = Path(self.name).suffix.lstrip(".")

@dataclass
class SearchResults:
    """Container for search results with metadata."""
    query: str
    total: int
    returned: int
    time_ms: float
    items: list[EverythingResult] = field(default_factory=list)


class EverythingBackend:
    """Backend for Everything search engine on Windows.

    Two transport modes:
    1. es.exe subprocess (primary — always available)
    2. HTTP API localhost:7331 (secondary — requires explicit server enable)
    """

    # Commands that Everything blocks for safety when called via IPC
    _ES_SAFE = frozenset(["search", "find", "query", "count", "recent", "list"])

    def __init__(
        self,
        es_path: Optional[str] = None,
        http_base: str = "http://localhost:7331",
    ) -> None:
        """Initialize backend.

        Args:
            es_path: Path to es.exe. Auto-detected if None (PATH + common locations).
            http_base: Base URL for Everything HTTP API.
        """
        self._es_path = self._find_es(es_path)
        self._http_base = http_base.rstrip("/")
        self._http_available: Optional[bool] = None

    # -- detection ----------------------------------------------------------

    @staticmethod
    def _find_es(explicit: Optional[str]) -> Optional[str]:
        """Find es.exe on the system."""
        if explicit and Path(explicit).exists():
            return explicit

        # 1. PATH
        found = shutil.which("es.exe") or shutil.which("es")
        if found:
            return found

        # 2. Common locations
        candidates = [
            Path.home() / "AppData" / "Local" / "Microsoft" / "WindowsApps" / "es.exe",
            Path("E:/Everything/es.exe"),
            Path("C:/Program Files/Everything/es.exe"),
        ]
        for c in candidates:
            if c.exists():
                return str(c)

        return None

    @property
    def available(self) -> bool:
        return self._es_path is not None

    @property
    def es_path(self) -> Optional[str]:
        return self._es_path

    # -- es.exe subprocess --------------------------------------------------

    def _run_es(self, args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Run es.exe safely."""
        if not self._es_path:
            raise RuntimeError("es.exe not found. Install it: winget install voidtools.Everything.Cli")

        cmd = [self._es_path] + args
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=0x08000000 if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"es.exe not found at {self._es_path}. "
                "Is Everything installed? https://www.voidtools.com"
            ) from exc

    def search(
        self,
        query: str,
        max_results: int = 50,
        match_path: bool = False,
        match_case: bool = False,
        match_whole_word: bool = False,
        regex: bool = False,
        sort_by: str = "name",
        folders_only: bool = False,
        files_only: bool = False,
    ) -> SearchResults:
        """Search files and folders.

        Args:
            query: Search text (supports Everything syntax).
            max_results: Maximum results (default 50).
            match_path: Match full path (not just filename).
            match_case: Case-sensitive search.
            match_whole_word: Whole word match.
            regex: Use regex pattern.
            sort_by: Sort field (name, path, size, date-modified, extension).
            folders_only: Only return folders.
            files_only: Only return files (not folders).

        Returns:
            SearchResults with matching items.
        """
        args: list[str] = []
        if match_path:
            args.append("-path")
        if match_case:
            args.append("-case")
        if match_whole_word:
            args.append("-wholeword")
        if regex:
            args.append("-regex")
        if folders_only:
            args.append("-ad")
        if files_only:
            args.append("-a-d")
        if sort_by == "size":
            args.append("-sort=size")
        elif sort_by == "path":
            args.append("-sort=path")
        elif sort_by == "date-modified":
            args.append("-sort=date-modified")
        elif sort_by == "extension":
            args.append("-sort=extension")
        args.append("-n")
        args.append(str(max_results))
        args.append(query)

        import time
        start = time.time()
        proc = self._run_es(args)
        elapsed = (time.time() - start) * 1000

        items = []
        for line in proc.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # es.exe output: "filename.ext" or "C:\path\to\filename.ext"
            p = Path(line)
            items.append(EverythingResult(
                name=p.name,
                path=str(p.parent) if p.parent != Path(".") else ".",
                full_path=line,
                extension=p.suffix.lstrip(".") if p.suffix else "",
            ))

        return SearchResults(
            query=query,
            total=len(items),
            returned=len(items),
            time_ms=round(elapsed, 1),
            items=items,
        )

    def list_by_extension(
        self, extension: str, max_results: int = 100, folder: Optional[str] = None
    ) -> SearchResults:
        """Find all files of a given extension, optionally within a folder.

        Args:
            extension: File extension (e.g. "pdf", "docx").
            max_results: Maximum number of results.
            folder: Optional folder to limit search scope.

        Returns:
            SearchResults.
        """
        query = f"ext:{extension}"
        if folder:
            query = f'"{folder}" {query}'
        return self.search(query, max_results=max_results)

    def find_recent(self, days: int = 1, max_results: int = 50) -> SearchResults:
        """Find files modified in the last N days.

        Args:
            days: Days back (default 1).
            max_results: Maximum results.

        Returns:
            SearchResults with recently modified files.
        """
        query = f"dm:last{days}days"
        return self.search(query, max_results=max_results)

    def count(self, query: str = "") -> int:
        """Get total count of items matching query (empty = total indexed)."""
        proc = self._run_es([query, "-n=0"])
        # es.exe outputs count line to stderr or last line
        stderr = proc.stderr.strip()
        if stderr and stderr.isdigit():
            return int(stderr)
        # Fallback: count output lines
        return len([l for l in proc.stdout.strip().split("\n") if l.strip()])

    def find_duplicates(self, by: str = "name", max_results: int = 100) -> SearchResults:
        """Find duplicate files (by name or size)."""
        query = "dupe:" if by == "name" else "sizedupe:"
        return self.search(query, max_results=max_results)

    def find_empty(self, folders_only: bool = False, max_results: int = 100) -> SearchResults:
        """Find empty files or folders."""
        query = "empty:" if not folders_only else "empty: folder:"
        return self.search(query, max_results=max_results)

    def find_large(self, min_size_mb: int = 100, max_results: int = 50) -> SearchResults:
        """Find large files (>= min_size_mb MB)."""
        query = f"size:>{min_size_mb}mb"
        return self.search(query, max_results=max_results, sort_by="size")

    # -- HTTP API (alternative transport) -----------------------------------

    def _check_http(self) -> bool:
        """Check if Everything HTTP server is running."""
        if self._http_available is not None:
            return self._http_available
        try:
            urllib.request.urlopen(f"{self._http_base}/", timeout=2)
            self._http_available = True
        except Exception:
            self._http_available = False
        return self._http_available

    def search_http(self, query: str, max_results: int = 50) -> SearchResults:
        """Search via Everything HTTP API (returns JSON automatically).

        Args:
            query: Search text.
            max_results: Maximum results.

        Returns:
            SearchResults parsed from HTTP JSON response.

        Raises:
            ConnectionError: If HTTP server is not enabled.
        """
        if not self._check_http():
            raise ConnectionError(
                "Everything HTTP server not available. "
                "Enable it: Tools → Options → HTTP Server → Enable HTTP Server"
            )

        encoded = urllib.parse.quote(query, safe="")
        url = f"{self._http_base}/?s={encoded}&j=1&path_column=1&c={max_results}"
        import time
        start = time.time()
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            elapsed = (time.time() - start) * 1000
        except Exception as exc:
            raise ConnectionError(f"HTTP API request failed: {exc}") from exc

        items = []
        results = data.get("results", []) if isinstance(data, dict) else []
        for r in results:
            name = r.get("name", "")
            full_path = r.get("path", "")
            p = Path(full_path) if full_path else Path(".")
            items.append(EverythingResult(
                name=name or p.name,
                path=str(p.parent) if full_path else r.get("path", "."),
                full_path=full_path or "",
                size=int(r.get("size", 0)),
                date_modified=r.get("date_modified", ""),
                extension=Path(name).suffix.lstrip(".") if name else "",
            ))

        return SearchResults(
            query=query,
            total=data.get("totalResults", len(items)),
            returned=len(items),
            time_ms=round(elapsed, 1),
            items=items,
        )

    # -- status ------------------------------------------------------------

    def status(self) -> dict:
        """Get backend diagnostic info."""
        http_up = self._check_http()
        count = 0
        try:
            count = self.count()
        except Exception:
            pass
        return {
            "available": self.available,
            "es_path": self._es_path,
            "http_api": http_up,
            "total_indexed": count,
        }
