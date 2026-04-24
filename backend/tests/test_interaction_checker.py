"""Unit tests for interaction_checker — Shehan's tool."""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from rxsentinel.config import settings
from rxsentinel.tools.interaction_checker import (
    check_interaction,
    query_openfda,
    severity_summary,
)


class TestLocalDB:
    @pytest.mark.asyncio
    async def test_known_severe_pair_returns_high(self, tmp_cache_dir) -> None:
        # warfarin (29046) + ibuprofen (5640) is in the seed CSV as "high".
        with respx.mock:
            respx.get(f"{settings.openfda_base_url}/drug/event.json").respond(
                404, json={}
            )
            records = await check_interaction("29046", "5640")
        assert len(records) == 1
        assert records[0].severity == "high"
        assert "local-db" in records[0].sources

    @pytest.mark.asyncio
    async def test_unknown_pair_returns_empty(self, tmp_cache_dir) -> None:
        with respx.mock:
            respx.get(f"{settings.openfda_base_url}/drug/event.json").respond(
                404, json={}
            )
            records = await check_interaction("99999999", "88888888")
        assert records == []

    @pytest.mark.asyncio
    async def test_same_drug_returns_empty(self, tmp_cache_dir) -> None:
        records = await check_interaction("29046", "29046")
        assert records == []

    @pytest.mark.asyncio
    async def test_empty_rxcui_returns_empty(self, tmp_cache_dir) -> None:
        records = await check_interaction("", "5640")
        assert records == []


class TestOpenFDA:
    @pytest.mark.asyncio
    async def test_query_with_results(self, tmp_cache_dir) -> None:
        with respx.mock:
            respx.get(f"{settings.openfda_base_url}/drug/event.json").respond(
                200,
                json={
                    "results": [
                        {"term": "acute kidney injury", "count": 1247},
                        {"term": "death", "count": 132},
                    ]
                },
            )
            result = await query_openfda("ibuprofen", "lisinopril")
        assert result["co_mention_count"] == 1379
        assert result["top_reactions"][0]["term"] == "acute kidney injury"
        assert result["severity_signal"] > 0

    @pytest.mark.asyncio
    async def test_query_404_returns_empty(self, tmp_cache_dir) -> None:
        with respx.mock:
            respx.get(f"{settings.openfda_base_url}/drug/event.json").respond(404)
            result = await query_openfda("bogus", "drugs")
        assert result["co_mention_count"] == 0
        assert result["top_reactions"] == []

    @pytest.mark.asyncio
    async def test_network_error_degrades_gracefully(self, tmp_cache_dir) -> None:
        with respx.mock:
            respx.get(f"{settings.openfda_base_url}/drug/event.json").mock(
                side_effect=Exception("boom")
            )
            result = await query_openfda("a", "b")
        assert result["co_mention_count"] == 0


class TestSeveritySummary:
    def test_counts_by_severity(self) -> None:
        from rxsentinel.tools.interaction_checker import InteractionRecord

        recs = [
            InteractionRecord("1", "2", "a", "b", "high", "m", "ce", "r"),
            InteractionRecord("1", "3", "a", "c", "moderate", "m", "ce", "r"),
            InteractionRecord("2", "3", "b", "c", "moderate", "m", "ce", "r"),
            InteractionRecord("4", "5", "d", "e", "low", "m", "ce", "r"),
        ]
        summary = severity_summary(recs)
        assert summary == {"high": 1, "moderate": 2, "low": 1}
