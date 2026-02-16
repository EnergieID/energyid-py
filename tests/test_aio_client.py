"""Tests for the async client."""

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from energyid.aio.client import (
    JSONClient as AsyncJSONClient,
    PandasClient as AsyncPandasClient,
)


# ── Structural Tests ─────────────────────────────────────────


class TestAsyncClientExists:
    """Verify all methods on the async client exist and are coroutine functions."""

    EXPECTED_METHODS = [
        "get_meter_catalog",
        "get_group",
        "get_group_records",
        "get_group_members",
        "get_group_meters",
        "get_group_my_records",
        "get_group_admins",
        "add_record_to_group",
        "change_reference_of_record_in_group",
        "remove_record_from_group",
        "get_member",
        "update_member",
        "get_member_limits",
        "set_member_language",
        "set_member_default_record",
        "set_member_default_record_page",
        "get_member_groups",
        "get_member_records",
        "get_meter",
        "get_meter_readings",
        "get_meter_latest_reading",
        "create_meter_reading",
        "create_meter",
        "hide_meter",
        "close_meter",
        "edit_meter",
        "get_meter_data",
        "get_meter_reading",
        "edit_meter_reading",
        "edit_meter_reading_status",
        "ignore_meter_reading",
        "delete_meter",
        "delete_meter_reading",
        "get_organization",
        "get_organization_groups",
        "get_record",
        "get_record_meters",
        "get_record_groups",
        "get_record_data",
        "get_record_directives",
        "get_record_directive_signals",
        "get_record_activity",
        "get_record_timeline",
        "create_timeline_item",
        "update_timeline_item",
        "delete_timeline_item",
        "get_record_limits",
        "get_record_benchmark",
        "get_record_benchmark_filtered",
        "create_record",
        "edit_record",
        "delete_record",
        "get_record_definitions",
        "search_groups",
        "search_services",
        "search_cities",
        "create_transfer",
        "cancel_transfer",
        "accept_transfer",
        "decline_transfer",
    ]

    def test_all_methods_exist(self):
        for method_name in self.EXPECTED_METHODS:
            assert hasattr(AsyncJSONClient, method_name), (
                f"AsyncJSONClient is missing method: {method_name}"
            )

    def test_all_methods_are_coroutines(self):
        for method_name in self.EXPECTED_METHODS:
            method = getattr(AsyncJSONClient, method_name)
            assert inspect.iscoroutinefunction(method), (
                f"AsyncJSONClient.{method_name} is not a coroutine function"
            )


# ── Auth Tests ───────────────────────────────────────────────


class TestAsyncClientAuth:
    def test_api_key_auth(self):
        client = AsyncJSONClient(api_key="test-key")
        assert client._auth_mode == "api_key"
        assert client._auth_headers == {"Authorization": "apiKey test-key"}

    def test_device_token_auth(self):
        client = AsyncJSONClient(device_token="dev-tok")
        assert client._auth_mode == "device_token"
        assert client._auth_headers == {"Authorization": "device dev-tok"}

    def test_oauth2_auth(self):
        client = AsyncJSONClient(client_id="cid", client_secret="csec")
        assert client._auth_mode == "oauth2"

    def test_no_auth_raises(self):
        with pytest.raises(ValueError):
            AsyncJSONClient()


class TestAsyncClientContextManager:
    def test_has_aenter_aexit(self):
        assert hasattr(AsyncJSONClient, "__aenter__")
        assert hasattr(AsyncJSONClient, "__aexit__")


class TestAsyncPandasClient:
    EXPECTED_METHODS = [
        "get_meter_readings",
        "get_meter_data",
        "get_record_data",
    ]

    def test_all_methods_exist(self):
        for method_name in self.EXPECTED_METHODS:
            assert hasattr(AsyncPandasClient, method_name)

    def test_all_methods_are_coroutines(self):
        for method_name in self.EXPECTED_METHODS:
            method = getattr(AsyncPandasClient, method_name)
            assert inspect.iscoroutinefunction(method), (
                f"AsyncPandasClient.{method_name} is not a coroutine function"
            )

    def test_inherits_from_json_client(self):
        assert issubclass(AsyncPandasClient, AsyncJSONClient)


# ── Functional Tests ─────────────────────────────────────────


def _mock_aiohttp_response(json_data=None, status=200):
    """Create a mock aiohttp response as an async context manager."""
    mock_resp = AsyncMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=json_data or {})
    mock_resp.raise_for_status = MagicMock()

    cm = AsyncMock()
    cm.__aenter__.return_value = mock_resp
    cm.__aexit__.return_value = None
    return cm


class TestAsyncFunctionalMembers:
    def setup_method(self):
        self.client = AsyncJSONClient(api_key="test-key")

    @pytest.mark.asyncio
    async def test_get_member(self):
        mock_cm = _mock_aiohttp_response({"id": "abc", "fullName": "Test User"})
        with patch.object(self.client.session, "request", return_value=mock_cm):
            member = await self.client.get_member()
            assert member["fullName"] == "Test User"
            assert member.id == "abc"

    @pytest.mark.asyncio
    async def test_get_member_records(self):
        mock_cm = _mock_aiohttp_response([{"id": 1}, {"id": 2}])
        with patch.object(self.client.session, "request", return_value=mock_cm):
            records = await self.client.get_member_records()
            assert len(records) == 2

    @pytest.mark.asyncio
    async def test_get_member_groups(self):
        mock_cm = _mock_aiohttp_response([{"id": "g1", "displayName": "Group"}])
        with patch.object(self.client.session, "request", return_value=mock_cm):
            groups = await self.client.get_member_groups()
            assert len(groups) == 1

    @pytest.mark.asyncio
    async def test_update_member(self):
        mock_cm = _mock_aiohttp_response(
            {"id": "abc", "fullName": "New", "initials": "NN"}
        )
        with patch.object(self.client.session, "request", return_value=mock_cm):
            member = await self.client.update_member("abc", "New", "NN")
            assert member["fullName"] == "New"


class TestAsyncFunctionalRecords:
    def setup_method(self):
        self.client = AsyncJSONClient(api_key="test-key")

    @pytest.mark.asyncio
    async def test_get_record(self):
        mock_cm = _mock_aiohttp_response({"id": 123, "displayName": "Home"})
        with patch.object(self.client.session, "request", return_value=mock_cm):
            record = await self.client.get_record(123)
            assert record.id == 123

    @pytest.mark.asyncio
    async def test_get_record_meters(self):
        mock_cm = _mock_aiohttp_response([{"id": "m1"}, {"id": "m2"}])
        with patch.object(self.client.session, "request", return_value=mock_cm):
            meters = await self.client.get_record_meters(123)
            assert len(meters) == 2

    @pytest.mark.asyncio
    async def test_get_record_definitions(self):
        mock_cm = _mock_aiohttp_response({"data": [{"name": "electricityImport"}]})
        with patch.object(self.client.session, "request", return_value=mock_cm):
            defs = await self.client.get_record_definitions("EA-123")
            assert defs[0]["name"] == "electricityImport"

    @pytest.mark.asyncio
    async def test_get_record_data(self):
        mock_cm = _mock_aiohttp_response({"value": []})
        with patch.object(self.client.session, "request", return_value=mock_cm):
            data = await self.client.get_record_data(
                123, "energyUse", "2024-01-01", "2024-12-31"
            )
            assert "value" in data

    @pytest.mark.asyncio
    async def test_create_record(self):
        mock_cm = _mock_aiohttp_response({"id": 999, "displayName": "New"})
        with patch.object(self.client.session, "request", return_value=mock_cm):
            record = await self.client.create_record(
                "New Home", "household", "Brussels", "1000", "bE", "dwelling"
            )
            assert record.id == 999

    @pytest.mark.asyncio
    async def test_delete_record(self):
        mock_cm = _mock_aiohttp_response({})
        with patch.object(self.client.session, "request", return_value=mock_cm):
            await self.client.delete_record(123)

    @pytest.mark.asyncio
    async def test_get_record_timeline(self):
        mock_cm = _mock_aiohttp_response([{"id": "t1", "displayName": "Solar"}])
        with patch.object(self.client.session, "request", return_value=mock_cm):
            items = await self.client.get_record_timeline(
                "EA-123", "2024-01-01", "2024-12-31"
            )
            assert len(items) == 1

    @pytest.mark.asyncio
    async def test_create_timeline_item(self):
        mock_cm = _mock_aiohttp_response({"id": "t-new"})
        with patch.object(self.client.session, "request", return_value=mock_cm):
            item = await self.client.create_timeline_item(
                "EA-123", "Solar", "2024-06-01"
            )
            assert item["id"] == "t-new"

    @pytest.mark.asyncio
    async def test_get_record_benchmark(self):
        mock_cm = _mock_aiohttp_response({"median": 5000, "count": 100})
        with patch.object(self.client.session, "request", return_value=mock_cm):
            bm = await self.client.get_record_benchmark(
                "EA-123", "electricityImport", 2024
            )
            assert bm["median"] == 5000


class TestAsyncFunctionalGroups:
    def setup_method(self):
        self.client = AsyncJSONClient(api_key="test-key")

    @pytest.mark.asyncio
    async def test_get_group(self):
        mock_cm = _mock_aiohttp_response({"id": "grp1", "displayName": "Group 1"})
        with patch.object(self.client.session, "request", return_value=mock_cm):
            group = await self.client.get_group("grp1")
            assert group["displayName"] == "Group 1"

    @pytest.mark.asyncio
    async def test_get_group_records(self):
        mock_cm = _mock_aiohttp_response([{"id": 1}])
        with patch.object(self.client.session, "request", return_value=mock_cm):
            records = await self.client.get_group_records("grp1")
            assert len(records) == 1

    @pytest.mark.asyncio
    async def test_get_group_meters(self):
        mock_cm = _mock_aiohttp_response([{"id": "m1"}])
        with patch.object(self.client.session, "request", return_value=mock_cm):
            meters = await self.client.get_group_meters("grp1")
            assert len(meters) == 1

    @pytest.mark.asyncio
    async def test_get_group_admins(self):
        mock_cm = _mock_aiohttp_response([{"id": "a1", "role": "owner"}])
        with patch.object(self.client.session, "request", return_value=mock_cm):
            admins = await self.client.get_group_admins("grp1")
            assert admins[0]["role"] == "owner"


class TestAsyncFunctionalMeters:
    def setup_method(self):
        self.client = AsyncJSONClient(api_key="test-key")

    @pytest.mark.asyncio
    async def test_get_meter(self):
        mock_cm = _mock_aiohttp_response({"id": "m1", "metric": "electricityImport"})
        with patch.object(self.client.session, "request", return_value=mock_cm):
            meter = await self.client.get_meter("m1")
            assert meter["metric"] == "electricityImport"

    @pytest.mark.asyncio
    async def test_create_meter_reading(self):
        mock_cm = _mock_aiohttp_response({"key": "k1", "value": 100})
        with patch.object(self.client.session, "request", return_value=mock_cm):
            reading = await self.client.create_meter_reading(
                "m1", value=100, timestamp="2024-01-01"
            )
            assert reading["value"] == 100

    @pytest.mark.asyncio
    async def test_get_meter_readings(self):
        mock_cm = _mock_aiohttp_response(
            {"readings": [{"key": "k1", "value": 50}], "nextRowKey": None}
        )
        with patch.object(self.client.session, "request", return_value=mock_cm):
            result = await self.client.get_meter_readings("m1")
            assert len(result["readings"]) == 1

    @pytest.mark.asyncio
    async def test_close_meter(self):
        mock_cm = _mock_aiohttp_response({})
        with patch.object(self.client.session, "request", return_value=mock_cm):
            await self.client.close_meter("m1", closed=True)

    @pytest.mark.asyncio
    async def test_delete_meter(self):
        mock_cm = _mock_aiohttp_response({})
        with patch.object(self.client.session, "request", return_value=mock_cm):
            await self.client.delete_meter("m1")


class TestAsyncFunctionalTransfers:
    def setup_method(self):
        self.client = AsyncJSONClient(api_key="test-key")

    @pytest.mark.asyncio
    async def test_create_transfer(self):
        mock_cm = _mock_aiohttp_response({"id": "tr1"})
        with patch.object(self.client.session, "request", return_value=mock_cm):
            result = await self.client.create_transfer("EA-123", "user@example.com")
            assert result["id"] == "tr1"

    @pytest.mark.asyncio
    async def test_accept_transfer(self):
        mock_cm = _mock_aiohttp_response({})
        with patch.object(self.client.session, "request", return_value=mock_cm):
            await self.client.accept_transfer("tr1")


class TestAsyncFunctionalSearch:
    def setup_method(self):
        self.client = AsyncJSONClient(api_key="test-key")

    @pytest.mark.asyncio
    async def test_search_groups(self):
        mock_cm = _mock_aiohttp_response([{"id": "g1"}])
        with patch.object(self.client.session, "request", return_value=mock_cm):
            groups = await self.client.search_groups(q="energy")
            assert len(groups) == 1

    @pytest.mark.asyncio
    async def test_search_services(self):
        mock_cm = _mock_aiohttp_response([{"id": "s1"}])
        with patch.object(self.client.session, "request", return_value=mock_cm):
            services = await self.client.search_services(q="solar")
            assert len(services) == 1


class TestAsyncFunctionalOrganizations:
    def setup_method(self):
        self.client = AsyncJSONClient(api_key="test-key")

    @pytest.mark.asyncio
    async def test_get_organization(self):
        mock_cm = _mock_aiohttp_response({"id": "org1", "displayName": "Org"})
        with patch.object(self.client.session, "request", return_value=mock_cm):
            org = await self.client.get_organization("org1")
            assert org["displayName"] == "Org"

    @pytest.mark.asyncio
    async def test_get_organization_groups(self):
        mock_cm = _mock_aiohttp_response([{"id": "g1"}])
        with patch.object(self.client.session, "request", return_value=mock_cm):
            groups = await self.client.get_organization_groups("org1")
            assert len(groups) == 1
