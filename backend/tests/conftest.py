"""Shared pytest fixtures."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make the backend package importable when running pytest from repo root.
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


@pytest.fixture
def tmp_cache_dir(tmp_path, monkeypatch):
    """Redirect tool caches into a temp dir per-test for isolation."""
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setenv("CACHE_DIR", str(cache))
    # Force config re-read
    from rxsentinel import config as cfg
    cfg.settings.cache_dir = cache
    return cache


@pytest.fixture
def request_id() -> str:
    return "test-req-0001"
