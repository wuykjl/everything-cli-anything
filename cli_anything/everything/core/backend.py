"""Everything Search backend — wraps es.exe (v1.1.0.31a+) with JSON output.

v2 — 2026-06-13: Upgraded to es.exe 1.1.0.31a native -json support.
Reliable post-filtering in Python for all compound queries.
"""
import json
import subprocess
import urllib.parse
import urllib.request
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── dataclasses ──────────────────────────────────────────────────────────

@dataclass
class EverythingResult:
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
    query: str
    total: int
    returned: int
    time_ms: float
    items: list[EverythingResult] = field(default_factory=list)


# ── backend ──────────────────────────────────────────────────────────────

class EverythingBackend:
    """Backend for Everything search engine on Windows.

    Requires Everything 1.4+ running and es.exe >= 1.1.0.31a on PATH.
    Two transports:
      1. es.exe subprocess with -json (primary)
      2. HTTP API localhost:7331 (secondary)
    """
    _MIN_ES_VERSION = "1.1.0.31a"

    def __init__(
        self, es_path: Optional[str] = None, http_base: str = "http://localhost:7331",
    ) -> None:
        self._es_path = self._find_es(es_path)
        self._http_base = http_base.rstrip("/")
        self._http_available: Optional[bool] = None

    # -- detection ---------------------------------------------------------

    @staticmethod
    def _find_es(explicit: Optional[str]) -> Optional[str]:
        if explicit and Path(explicit).exists():
            return explicit
        found = shutil.which("es.exe") or shutil.which("es")
        if found:
            return found
        for c in [
            Path("E:/Everything/es.exe"),
            Path.home() / "AppData/Local/Microsoft/WindowsApps/es.exe",
            Path("C:/Program Files/Everything/es.exe"),
        ]:
            if c.exists():
                return str(c)
        return None

    @property
    def available(self) -> bool:
        return self._es_path is not None

    @property
    def es_path(self) -> Optional[str]:
        return self._es_path

    # -- es.exe subprocess (v1.1.0.31a -json) -----------------------------

    def _run_es(self, args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
        if not self._es_path:
            raise RuntimeError(
                "es.exe not found. Install Everything and es.exe 1.1.0.31a+: "
                "https://www.voidtools.com"
            )
        cmd = [self._es_path] + args
        try:
            return subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
                creationflags=0x08000000 if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
        except FileNotFoundError:
            raise RuntimeError(f"es.exe not found at {self._es_path}")

    def _parse_json_output(self, stdout: str) -> list[dict]:
        """Parse es.exe -json output into a list of result dicts."""
        if not stdout.strip():
            return []
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            # Fallback: parse line-by-line (older versions)
            items = []
            for line in stdout.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    items.append({"filename": line})
            return items

    def _results_from_json(self, raw: list[dict]) -> list[EverythingResult]:
        out = []
        for r in raw:
            fp = r.get("filename", "")
            if not fp:
                continue
            p = Path(fp)
            out.append(EverythingResult(
                name=p.name,
                path=str(p.parent) if p.parent != Path(".") else ".",
                full_path=fp,
                size=int(r.get("size", 0)),
                date_modified=r.get("datemodified", ""),
                extension=p.suffix.lstrip(".") if p.suffix else "",
            ))
        return out

    def search(
        self, query: str, max_results: int = 50, folders_only: bool = False,
        files_only: bool = False,
    ) -> SearchResults:
        """Search files and folders. Everything syntax support depends on version.

        For 1.1.0.31a+, uses native -json output.
        Compound filters (ext: + keywords) are post-filtered in Python.
        """
        args = ["-n", str(max_results), "-json", query]
        if folders_only:
            args.insert(2, "-ad")
        if files_only:
            args.insert(2, "-a-d")

        t0 = time.time()
        proc = self._run_es(args)
        elapsed = (time.time() - t0) * 1000

        raw = self._parse_json_output(proc.stdout)
        items = self._results_from_json(raw)
        return SearchResults(
            query=query, total=len(items), returned=len(items),
            time_ms=round(elapsed, 1), items=items,
        )

    def list_by_extension(
        self, extension: str, max_results: int = 100, folder: Optional[str] = None,
    ) -> SearchResults:
        """Find all files of a given extension, optionally within a folder.

        Uses Everything's substring match for filename patterns.
        Caveat when folder is specified: relies on post-filtering in Python.
        Very large disks may not return all matches if the target folder
        is outside the first 5000 results. Use `search <name>` for targeted lookups.
        """
        t0 = time.time()
        search_max = 8000 if folder else 3000

        # Primary: search for the filename extension literally
        results = self.search(f".{extension}", max_results=search_max)

        # Secondary (folder-scoped): scan dir + search by filename (bypasses MFT order)
        if folder:
            try:
                dir_entries = list(Path(folder).rglob(f"*.{extension}"))
                for fpath in dir_entries:
                    name_only = fpath.name
                    s = self.search(name_only, max_results=5)
                    for it in s.items:
                        if it.extension == extension:
                            results.items.append(it)
                # Deduplicate
                seen_paths = set()
                unique_items = []
                for it in results.items:
                    if it.full_path not in seen_paths:
                        seen_paths.add(it.full_path)
                        unique_items.append(it)
                results.items = unique_items
            except Exception:
                pass  # rglob can fail on permission errors; silent fallback

        elapsed = (time.time() - t0) * 1000

        # Python post-filter: exact extension match
        filtered = [it for it in results.items if it.extension == extension]
        # Python post-filter: path prefix (when folder specified)
        if folder:
            fn = str(Path(folder)).replace("\\", "/").rstrip("/") + "/"
            filtered = [it for it in filtered
                        if it.full_path.replace("\\", "/").startswith(fn)]

        return SearchResults(
            query=f"ext:{extension}" + (f" in {folder}" if folder else ""),
            total=len(filtered),
            returned=min(len(filtered), max_results),
            time_ms=round(elapsed, 1),
            items=filtered[:max_results],
        )

    def find_recent(self, days: int = 1, max_results: int = 50) -> SearchResults:
        query = f"dm:last{days}days"
        return self.search(query, max_results=max_results)

    def count(self, query: str = "") -> int:
        """Get total indexed item count. Uses HTTP API for reliable data."""
        try:
            if self._check_http():
                encoded = urllib.parse.quote(query or ".", safe="")
                url = f"{self._http_base}/?s={encoded}&j=1&c=1"
                with urllib.request.urlopen(url, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return int(data.get("totalResults", 0))
        except Exception:
            pass
        # Fallback: es.exe broad search, count lines
        proc = self._run_es(["-n", "500", query or "."])
        return len([l for l in proc.stdout.strip().split("\n") if l.strip()])

    def find_duplicates(self, by: str = "name", max_results: int = 100) -> SearchResults:
        query = "dupe:" if by == "name" else "sizedupe:"
        return self.search(query, max_results=max_results)

    def find_empty(self, folders_only: bool = False, max_results: int = 100) -> SearchResults:
        query = "empty:" if not folders_only else "empty:"
        return self.search(query, max_results=max_results, folders_only=folders_only)

    def find_large(self, min_size_mb: int = 100, max_results: int = 50) -> SearchResults:
        return self.search(f"size:>{min_size_mb}mb", max_results=max_results)

    # -- HTTP API (alternative) -------------------------------------------

    def _check_http(self) -> bool:
        if self._http_available is not None:
            return self._http_available
        try:
            urllib.request.urlopen(f"{self._http_base}/", timeout=2)
            self._http_available = True
        except Exception:
            self._http_available = False
        return self._http_available

    def search_http(self, query: str, max_results: int = 50) -> SearchResults:
        if not self._check_http():
            raise ConnectionError(
                "Everything HTTP server not available. "
                "Enable: Tools → Options → HTTP Server → Enable HTTP Server"
            )
        encoded = urllib.parse.quote(query, safe="")
        url = f"{self._http_base}/?s={encoded}&j=1&path_column=1&c={max_results}"
        t0 = time.time()
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise ConnectionError(f"HTTP API request failed: {exc}") from exc
        elapsed = (time.time() - t0) * 1000

        items = []
        for r in data.get("results", []) if isinstance(data, dict) else []:
            name = r.get("name", "")
            fp = r.get("path", "")
            p = Path(fp) if fp else Path(".")
            items.append(EverythingResult(
                name=name or p.name, path=str(p.parent) if fp else r.get("path", "."),
                full_path=fp or "", size=int(r.get("size", 0)),
                date_modified=r.get("date_modified", ""),
                extension=Path(name).suffix.lstrip(".") if name else "",
            ))
        return SearchResults(
            query=query, total=data.get("totalResults", len(items)),
            returned=len(items), time_ms=round(elapsed, 1), items=items,
        )

    def status(self) -> dict:
        http_up = self._check_http()
        total = 0
        try:
            total = self.count()
        except Exception:
            pass
        return {
            "available": self.available,
            "es_path": self._es_path,
            "http_api": http_up,
            "total_indexed": total,
        }
