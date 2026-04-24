"""Unit tests for rxnorm_lookup — Thusala's tool.

HTTP calls to the RxNorm API are mocked with respx; tests run offline.
"""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from rxsentinel.config import settings
from rxsentinel.tools.rxnorm_lookup import rxnorm_lookup


class TestExactMatch:
    @pytest.mark.asyncio
    async def test_exact_brand_resolves(self, tmp_cache_dir) -> None:
        with respx.mock:
            respx.get(f"{settings.rxnorm_base_url}/rxcui.json").respond(
                200,
                json={"idGroup": {"name": "Tylenol", "rxnormId": ["1191"]}},
            )
            result = await rxnorm_lookup("Tylenol")
        assert result.rxcui == "1191"
        assert result.confidence == 1.0
        assert result.source == "exact"


class TestApproximateMatch:
    @pytest.mark.asyncio
    async def test_misspelling_resolves_via_fuzzy(self, tmp_cache_dir) -> None:
        with respx.mock:
            respx.get(f"{settings.rxnorm_base_url}/rxcui.json").respond(
                200, json={"idGroup": {"name": "metfromin"}}
            )
            respx.get(f"{settings.rxnorm_base_url}/approximateTerm.json").respond(
                200,
                json={
                    "approximateGroup": {
                        "candidate": [
                            {"rxcui": "6809", "name": "metformin", "score": "85"},
                            {"rxcui": "9999", "name": "metoprolol", "score": "60"},
                        ]
                    }
                },
            )
            result = await rxnorm_lookup("metfromin")
        assert result.rxcui == "6809"
        assert 0.5 <= result.confidence <= 1.0
        assert result.source == "approximate"
        assert len(result.alternatives) >= 1


class TestNoMatch:
    @pytest.mark.asyncio
    async def test_garbage_returns_none(self, tmp_cache_dir) -> None:
        with respx.mock:
            respx.get(f"{settings.rxnorm_base_url}/rxcui.json").respond(
                200, json={"idGroup": {"name": "asdfghjkl"}}
            )
            respx.get(f"{settings.rxnorm_base_url}/approximateTerm.json").respond(
                200, json={"approximateGroup": {}}
            )
            result = await rxnorm_lookup("asdfghjkl")
        assert result.rxcui is None
        assert result.confidence == 0.0


class TestEmpty:
    @pytest.mark.asyncio
    async def test_empty_string(self, tmp_cache_dir) -> None:
        result = await rxnorm_lookup("")
        assert result.rxcui is None
        assert result.confidence == 0.0


class TestCache:
    @pytest.mark.asyncio
    async def test_cache_hit_avoids_api(self, tmp_cache_dir) -> None:
        with respx.mock:
            route = respx.get(f"{settings.rxnorm_base_url}/rxcui.json").respond(
                200, json={"idGroup": {"name": "aspirin", "rxnormId": ["1191"]}}
            )
            r1 = await rxnorm_lookup("aspirin")
            r2 = await rxnorm_lookup("aspirin")
        assert r1.rxcui == r2.rxcui == "1191"
        # Second call should hit cache, not API.
        assert route.call_count == 1
        assert r2.source == "cache"
