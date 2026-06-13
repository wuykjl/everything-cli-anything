"""Tests for Everything backend (runs only when Everything is installed)."""
import sys
from pathlib import Path

import pytest

from cli_anything.everything.core.backend import EverythingBackend, EverythingResult, SearchResults


def test_backend_init():
    """Backend should construct without crashing."""
    backend = EverythingBackend()
    assert backend is not None
    # on a machine without Everything, available will be False
    if backend.available:
        assert backend.es_path is not None


def test_search_results_dataclass():
    result = EverythingResult(name="test.pdf", path="C:/Docs", full_path="C:/Docs/test.pdf")
    assert result.name == "test.pdf"
    assert result.extension == "pdf"
    assert result.full_path == "C:/Docs/test.pdf"


def test_search_results_container():
    r = SearchResults(query="test", total=42, returned=10, time_ms=15.5)
    assert r.total == 42
    assert r.time_ms == 15.5
    assert r.items == []


@pytest.mark.skipif(
    not EverythingBackend().available,
    reason="Everything/es.exe not installed on this machine"
)
class TestIntegration:
    """Integration tests — require Everything to be running."""

    def test_search_basic(self):
        backend = EverythingBackend()
        results = backend.search("explorer", max_results=5)
        assert results.total >= 0
        assert isinstance(results.time_ms, float)

    def test_search_by_extension(self):
        backend = EverythingBackend()
        results = backend.list_by_extension("exe", max_results=10)
        assert results.returned >= 0
        if results.items:
            # Everything may return '.exe.mui' or other variants alongside '.exe'
            # Verify at least one result with target extension
            exe_hits = [it for it in results.items if it.extension == "exe"]
            assert len(exe_hits) > 0, f"No .exe results found; got exts: {[it.extension for it in results.items[:5]]}"

    def test_count(self):
        backend = EverythingBackend()
        count = backend.count()
        assert count > 0  # indexed system should have millions

    def test_status(self):
        backend = EverythingBackend()
        info = backend.status()
        assert info["available"] is True
        assert isinstance(info["total_indexed"], int)

    def test_recent(self):
        backend = EverythingBackend()
        results = backend.find_recent(days=7, max_results=10)
        assert results.returned >= 0

    def test_find_large(self):
        backend = EverythingBackend()
        results = backend.find_large(min_size_mb=1000, max_results=5)
        assert results.returned >= 0

    def test_duplicates(self):
        backend = EverythingBackend()
        results = backend.find_duplicates(by="name", max_results=20)
        assert results.returned >= 0


def test_backend_not_available_graceful(monkeypatch):
    """When es.exe is not found anywhere, methods should raise clear errors."""
    backend = EverythingBackend(es_path="/nonexistent/es.exe")

    # Also mock shutil.which to return None (no PATH fallback)
    monkeypatch.setattr("shutil.which", lambda _: None)
    # Re-init to trigger resolution with mocked environment
    backend._es_path = EverythingBackend._find_es("/nonexistent/es.exe")
    # Monkeypatch the find function to always return None
    monkeypatch.setattr(backend, "_es_path", None)

    assert not backend.available
    with pytest.raises(RuntimeError, match="es.exe not found"):
        backend.search("test")
