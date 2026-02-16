"""Tests for the sync JSONClient."""

from unittest.mock import patch, MagicMock
import pytest

from energyid import JSONClient
from energyid.models import Member, Record, Meter, Group, Organization


# ── Auth Tests ────────────────────────────────────────────────


class TestAPIKeyAuth:
    def test_api_key_sets_header(self):
        client = JSONClient(api_key="test-key-123")
        assert client.session.headers["Authorization"] == "apiKey test-key-123"

    def test_api_key_auth_mode(self):
        client = JSONClient(api_key="test-key-123")
        assert client._auth_mode == "api_key"

    def test_api_key_skips_oauth(self):
        client = JSONClient(api_key="test-key-123")
        assert client._client_id is None
        assert client._client_secret is None


class TestDeviceTokenAuth:
    def test_device_token_sets_header(self):
        client = JSONClient(device_token="device-token-456")
        assert client.session.headers["Authorization"] == "device device-token-456"

    def test_device_token_auth_mode(self):
        client = JSONClient(device_token="device-token-456")
        assert client._auth_mode == "device_token"


class TestOAuth2Auth:
    def test_oauth2_auth_mode(self):
        client = JSONClient(client_id="cid", client_secret="csec")
        assert client._auth_mode == "oauth2"

    def test_oauth2_token_setter_uses_bearer(self):
        client = JSONClient(client_id="cid", client_secret="csec")
        client.token = "my-access-token"
        assert client.session.headers["Authorization"] == "Bearer my-access-token"

    def test_oauth2_auto_authenticate(self):
        client = JSONClient(
            client_id="cid",
            client_secret="csec",
            username="user",
            password="pass",
        )
        mock_auth_response = MagicMock()
        mock_auth_response.json.return_value = {
            "access_token": "token123",
            "refresh_token": "refresh123",
            "expires_in": 3600,
        }
        mock_auth_response.raise_for_status.return_value = None

        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {"id": "abc", "fullName": "Test"}
        mock_get_response.raise_for_status.return_value = None

        with patch.object(client.session, "post", return_value=mock_auth_response):
            with patch.object(client.session, "get", return_value=mock_get_response):
                member = client.get_member()
                assert member["fullName"] == "Test"


class TestAuthValidation:
    def test_no_auth_raises_error(self):
        with pytest.raises(ValueError, match="You must provide"):
            JSONClient()


# ── Request Tests ─────────────────────────────────────────────


class TestRequest:
    def setup_method(self):
        self.client = JSONClient(api_key="test-key")

    def _mock_response(self, json_data=None, status_code=200):
        mock = MagicMock()
        mock.json.return_value = json_data or {}
        mock.raise_for_status.return_value = None
        mock.status_code = status_code
        return mock

    def test_no_lru_cache_on_request(self):
        """Verify _request is not cached (the lru_cache bug was removed)."""
        assert not hasattr(self.client._request, "cache_info")

    def test_request_filters_none_params(self):
        mock_resp = self._mock_response({"result": "ok"})
        with patch.object(
            self.client.session, "get", return_value=mock_resp
        ) as mock_get:
            self.client._request("GET", "test", foo="bar", baz=None)
            args, kwargs = mock_get.call_args
            assert "baz" not in kwargs.get("params", {})
            assert kwargs["params"]["foo"] == "bar"


# ── Catalog Tests ─────────────────────────────────────────────


class TestCatalogs:
    def setup_method(self):
        self.client = JSONClient(api_key="test-key")

    def test_get_meter_catalog(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"metric": "electricityImport"}]
        mock_resp.raise_for_status.return_value = None
        with patch.object(
            self.client.session, "get", return_value=mock_resp
        ) as mock_get:
            self.client.get_meter_catalog()
            mock_get.assert_called_once()
            assert "catalogs/meters" in mock_get.call_args[0][0]


# ── Group Tests ───────────────────────────────────────────────


class TestGroups:
    def setup_method(self):
        self.client = JSONClient(api_key="test-key")
        self.mock_resp = MagicMock()
        self.mock_resp.raise_for_status.return_value = None

    def test_get_group(self):
        self.mock_resp.json.return_value = {"id": "grp1", "displayName": "Group 1"}
        with patch.object(self.client.session, "get", return_value=self.mock_resp):
            group = self.client.get_group("grp1")
            assert isinstance(group, Group)
            assert group["id"] == "grp1"

    def test_get_group_records(self):
        self.mock_resp.json.return_value = [
            {"id": 1, "displayName": "Rec1"},
            {"id": 2, "displayName": "Rec2"},
        ]
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            records = self.client.get_group_records("grp1")
            assert len(records) == 2
            assert all(isinstance(r, Record) for r in records)
            # Verify take parameter is used (not top)
            args, kwargs = mock_get.call_args
            assert "take" in kwargs["params"]
            assert "top" not in kwargs["params"]

    def test_get_group_members_uses_take(self):
        self.mock_resp.json.return_value = [{"id": "u1"}]
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            self.client.get_group_members("grp1", take=50, skip=10)
            args, kwargs = mock_get.call_args
            assert kwargs["params"]["take"] == 50
            assert kwargs["params"]["skip"] == 10

    def test_get_group_meters(self):
        self.mock_resp.json.return_value = [{"id": "m1", "metric": "electricityImport"}]
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            meters = self.client.get_group_meters("grp1")
            assert len(meters) == 1
            assert isinstance(meters[0], Meter)
            assert "groups/grp1/meters" in mock_get.call_args[0][0]

    def test_get_group_my_records(self):
        self.mock_resp.json.return_value = [{"id": 1}]
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            records = self.client.get_group_my_records("grp1")
            assert len(records) == 1
            assert "groups/grp1/records/mine" in mock_get.call_args[0][0]

    def test_get_group_admins(self):
        self.mock_resp.json.return_value = [{"id": "admin1", "displayName": "Admin"}]
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            admins = self.client.get_group_admins("grp1")
            assert len(admins) == 1
            assert "groups/grp1/admins" in mock_get.call_args[0][0]

    def test_add_record_to_group(self):
        self.mock_resp.json.return_value = {}
        with patch.object(self.client.session, "post", return_value=self.mock_resp):
            self.client.add_record_to_group("grp1", 123)

    def test_change_reference_of_record_in_group(self):
        self.mock_resp.json.return_value = {}
        with patch.object(
            self.client.session, "put", return_value=self.mock_resp
        ) as mock_put:
            self.client.change_reference_of_record_in_group("grp1", 123, "REF-001")
            assert "groups/grp1/records/123/reference" in mock_put.call_args[0][0]
            assert kwargs_params(mock_put)["reference"] == "REF-001"

    def test_remove_record_from_group(self):
        self.mock_resp.json.return_value = {}
        with patch.object(self.client.session, "delete", return_value=self.mock_resp):
            self.client.remove_record_from_group("grp1", 123)


# ── Member Tests ──────────────────────────────────────────────


class TestMembers:
    def setup_method(self):
        self.client = JSONClient(api_key="test-key")
        self.mock_resp = MagicMock()
        self.mock_resp.raise_for_status.return_value = None

    def test_get_member_default_me(self):
        self.mock_resp.json.return_value = {"id": "abc", "fullName": "Test User"}
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            member = self.client.get_member()
            assert isinstance(member, Member)
            assert member["fullName"] == "Test User"
            assert "members/me" in mock_get.call_args[0][0]

    def test_get_member_by_id(self):
        self.mock_resp.json.return_value = {"id": "xyz", "fullName": "Other"}
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            self.client.get_member("xyz")
            assert "members/xyz" in mock_get.call_args[0][0]

    def test_update_member(self):
        self.mock_resp.json.return_value = {
            "id": "abc",
            "fullName": "New Name",
            "initials": "NN",
        }
        with patch.object(
            self.client.session, "put", return_value=self.mock_resp
        ) as mock_put:
            member = self.client.update_member("abc", "New Name", "NN", biography="Bio")
            assert isinstance(member, Member)
            args, kwargs = mock_put.call_args
            assert kwargs["params"]["fullName"] == "New Name"
            assert kwargs["params"]["initials"] == "NN"
            assert kwargs["params"]["biography"] == "Bio"

    def test_get_member_limits(self):
        self.mock_resp.json.return_value = [{"name": "records", "limit": 10}]
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            self.client.get_member_limits()
            assert "members/me/limits" in mock_get.call_args[0][0]

    def test_set_member_language(self):
        self.mock_resp.json.return_value = {"id": "abc", "lang": "nl"}
        with patch.object(
            self.client.session, "put", return_value=self.mock_resp
        ) as mock_put:
            member = self.client.set_member_language("abc", "nl")
            assert isinstance(member, Member)
            assert kwargs_params(mock_put)["lang"] == "nl"

    def test_set_member_default_record(self):
        self.mock_resp.json.return_value = {"id": "abc"}
        with patch.object(
            self.client.session, "put", return_value=self.mock_resp
        ) as mock_put:
            self.client.set_member_default_record("abc", "EA-123")
            assert kwargs_params(mock_put)["recordId"] == "EA-123"

    def test_set_member_default_record_page(self):
        self.mock_resp.json.return_value = {"id": "abc"}
        with patch.object(
            self.client.session, "put", return_value=self.mock_resp
        ) as mock_put:
            self.client.set_member_default_record_page("abc", "dashboard")
            assert kwargs_params(mock_put)["page"] == "dashboard"

    def test_get_member_groups(self):
        self.mock_resp.json.return_value = [{"id": "g1"}]
        with patch.object(self.client.session, "get", return_value=self.mock_resp):
            groups = self.client.get_member_groups()
            assert all(isinstance(g, Group) for g in groups)

    def test_get_member_records_with_filters(self):
        self.mock_resp.json.return_value = [{"id": 1}]
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            records = self.client.get_member_records(
                filter="open", accessLevel="owner", expand="none"
            )
            assert len(records) == 1
            params = kwargs_params(mock_get)
            assert params["filter"] == "open"
            assert params["accessLevel"] == "owner"
            assert params["expand"] == "none"


# ── Meter Tests ───────────────────────────────────────────────


class TestMeters:
    def setup_method(self):
        self.client = JSONClient(api_key="test-key")
        self.mock_resp = MagicMock()
        self.mock_resp.raise_for_status.return_value = None

    def test_get_meter(self):
        self.mock_resp.json.return_value = {
            "id": "meter1",
            "metric": "electricityImport",
        }
        with patch.object(self.client.session, "get", return_value=self.mock_resp):
            meter = self.client.get_meter("meter1")
            assert isinstance(meter, Meter)

    def test_create_meter_no_prefix(self):
        """Verify create_meter does NOT hardcode EA- prefix."""
        self.mock_resp.json.return_value = {"id": "new-meter"}
        with patch.object(
            self.client.session, "post", return_value=self.mock_resp
        ) as mock_post:
            self.client.create_meter(
                record_id="EA-14092736",
                display_name="Test",
                metric="electricityImport",
                unit="kilowattHour",
                reading_type="counter",
            )
            params = kwargs_params(mock_post)
            assert params["recordId"] == "EA-14092736"
            # Should NOT prepend EA-
            assert not params["recordId"].startswith("EA-EA-")

    def test_close_meter(self):
        self.mock_resp.json.return_value = {}
        with patch.object(
            self.client.session, "put", return_value=self.mock_resp
        ) as mock_put:
            self.client.close_meter("meter1", closed=True)
            assert "meters/meter1/closed" in mock_put.call_args[0][0]
            assert kwargs_params(mock_put)["value"] is True

    def test_get_meter_latest_reading(self):
        self.mock_resp.json.return_value = {"key": "k1", "value": 999}
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            self.client.get_meter_latest_reading("meter1")
            assert "meters/meter1/readings/latest" in mock_get.call_args[0][0]

    def test_get_meter_reading_by_key(self):
        self.mock_resp.json.return_value = {"key": "k1", "value": 500}
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            self.client.get_meter_reading("meter1", "k1")
            assert "meters/meter1/readings/k1" in mock_get.call_args[0][0]

    def test_edit_meter_reading_status(self):
        self.mock_resp.json.return_value = {}
        with patch.object(
            self.client.session, "put", return_value=self.mock_resp
        ) as mock_put:
            self.client.edit_meter_reading_status("meter1", "k1", "verified")
            assert "meters/meter1/readings/k1/status" in mock_put.call_args[0][0]

    def test_ignore_meter_reading(self):
        self.mock_resp.json.return_value = {}
        with patch.object(
            self.client.session, "put", return_value=self.mock_resp
        ) as mock_put:
            self.client.ignore_meter_reading("meter1", "k1", ignore=True)
            assert "meters/meter1/readings/k1/ignore" in mock_put.call_args[0][0]

    def test_hide_meter(self):
        self.mock_resp.json.return_value = {"id": "meter1", "hidden": True}
        with patch.object(
            self.client.session, "post", return_value=self.mock_resp
        ) as mock_post:
            self.client.hide_meter("meter1", hidden=True)
            assert "meters/meter1/hidden" in mock_post.call_args[0][0]

    def test_edit_meter(self):
        self.mock_resp.json.return_value = {"id": "meter1"}
        with patch.object(
            self.client.session, "put", return_value=self.mock_resp
        ) as mock_put:
            self.client.edit_meter("meter1", displayName="Renamed")
            assert kwargs_params(mock_put)["displayName"] == "Renamed"

    def test_get_meter_data(self):
        self.mock_resp.json.return_value = {"data": []}
        with patch.object(self.client.session, "get", return_value=self.mock_resp):
            result = self.client.get_meter_data(
                "meter1", start="2024-01-01", end="2024-03-01"
            )
            assert isinstance(result, list)

    def test_get_meter_readings(self):
        self.mock_resp.json.return_value = {"readings": [], "nextRowKey": None}
        with patch.object(self.client.session, "get", return_value=self.mock_resp):
            result = self.client.get_meter_readings("meter1")
            assert "readings" in result

    def test_create_meter_reading(self):
        self.mock_resp.json.return_value = {"key": "k1", "value": 100}
        with patch.object(
            self.client.session, "post", return_value=self.mock_resp
        ) as mock_post:
            self.client.create_meter_reading(
                "meter1", value=100, timestamp="2024-01-01"
            )
            params = kwargs_params(mock_post)
            assert params["value"] == 100

    def test_edit_meter_reading(self):
        self.mock_resp.json.return_value = {"key": "k1", "value": 200}
        with patch.object(
            self.client.session, "put", return_value=self.mock_resp
        ) as mock_put:
            self.client.edit_meter_reading("meter1", "k1", 200)
            params = kwargs_params(mock_put)
            assert params["newValue"] == 200

    def test_delete_meter(self):
        self.mock_resp.json.return_value = {}
        with patch.object(self.client.session, "delete", return_value=self.mock_resp):
            self.client.delete_meter("meter1")

    def test_delete_meter_reading(self):
        self.mock_resp.json.return_value = {}
        with patch.object(self.client.session, "delete", return_value=self.mock_resp):
            self.client.delete_meter_reading("meter1", "k1")


# ── Organization Tests ────────────────────────────────────────


class TestOrganizations:
    def setup_method(self):
        self.client = JSONClient(api_key="test-key")
        self.mock_resp = MagicMock()
        self.mock_resp.raise_for_status.return_value = None

    def test_get_organization(self):
        self.mock_resp.json.return_value = {"id": "org1", "displayName": "Org"}
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            org = self.client.get_organization("org1")
            assert isinstance(org, Organization)
            assert "organizations/org1" in mock_get.call_args[0][0]

    def test_get_organization_groups(self):
        self.mock_resp.json.return_value = [{"id": "g1"}]
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            groups = self.client.get_organization_groups("org1", lang="nl")
            assert all(isinstance(g, Group) for g in groups)
            params = kwargs_params(mock_get)
            assert params["lang"] == "nl"


# ── Record Tests ──────────────────────────────────────────────


class TestRecords:
    def setup_method(self):
        self.client = JSONClient(api_key="test-key")
        self.mock_resp = MagicMock()
        self.mock_resp.raise_for_status.return_value = None

    def test_get_record(self):
        self.mock_resp.json.return_value = {"id": 123, "displayName": "Home"}
        with patch.object(self.client.session, "get", return_value=self.mock_resp):
            record = self.client.get_record(123)
            assert isinstance(record, Record)

    def test_get_record_meters(self):
        self.mock_resp.json.return_value = [{"id": "m1"}, {"id": "m2"}]
        with patch.object(self.client.session, "get", return_value=self.mock_resp):
            meters = self.client.get_record_meters(123)
            assert len(meters) == 2
            assert all(isinstance(m, Meter) for m in meters)

    def test_get_record_directives(self):
        self.mock_resp.json.return_value = [{"id": "d1", "name": "Dir1"}]
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            self.client.get_record_directives("EA-123")
            assert "records/EA-123/directives" in mock_get.call_args[0][0]

    def test_get_record_directive_signals(self):
        self.mock_resp.json.return_value = {"signals": []}
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            self.client.get_record_directive_signals("EA-123", "dir1", limit=10)
            params = kwargs_params(mock_get)
            assert params["limit"] == 10

    def test_get_record_activity(self):
        self.mock_resp.json.return_value = {"entries": [], "nextRowKey": None}
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            self.client.get_record_activity("EA-123", take=50)
            params = kwargs_params(mock_get)
            assert params["take"] == 50

    def test_get_record_timeline(self):
        self.mock_resp.json.return_value = [{"id": "t1"}]
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            self.client.get_record_timeline("EA-123", "2024-01-01", "2024-12-31")
            params = kwargs_params(mock_get)
            assert params["from"] == "2024-01-01"
            assert params["to"] == "2024-12-31"

    def test_create_timeline_item(self):
        self.mock_resp.json.return_value = {"id": "t-new"}
        with patch.object(
            self.client.session, "post", return_value=self.mock_resp
        ) as mock_post:
            self.client.create_timeline_item(
                "EA-123", "Solar installed", "2024-06-01", type="investment"
            )
            params = kwargs_params(mock_post)
            assert params["displayName"] == "Solar installed"
            assert params["type"] == "investment"

    def test_update_timeline_item(self):
        self.mock_resp.json.return_value = {"id": "t1"}
        with patch.object(
            self.client.session, "put", return_value=self.mock_resp
        ) as mock_put:
            self.client.update_timeline_item("EA-123", "t1", "Updated", "2024-06-01")
            assert "records/EA-123/timeline/t1" in mock_put.call_args[0][0]

    def test_delete_timeline_item(self):
        self.mock_resp.json.return_value = {}
        with patch.object(self.client.session, "delete", return_value=self.mock_resp):
            self.client.delete_timeline_item("EA-123", "t1")

    def test_get_record_limits(self):
        self.mock_resp.json.return_value = [{"name": "meters"}]
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            self.client.get_record_limits("EA-123")
            assert "records/EA-123/limits" in mock_get.call_args[0][0]

    def test_get_record_benchmark(self):
        self.mock_resp.json.return_value = {"median": 5000, "count": 100}
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            self.client.get_record_benchmark(
                "EA-123", "electricityImport", 2024, month=6
            )
            params = kwargs_params(mock_get)
            assert params["year"] == 2024
            assert params["month"] == 6

    def test_get_record_benchmark_filtered(self):
        self.mock_resp.json.return_value = {"median": 4000}
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            self.client.get_record_benchmark_filtered(
                "EA-123", "electricityImport", "carrier", 2024
            )
            url = mock_get.call_args[0][0]
            assert "benchmark/electricityImport/carrier" in url

    def test_create_record_required_params_only(self):
        self.mock_resp.json.return_value = {"id": 999, "displayName": "New"}
        with patch.object(
            self.client.session, "post", return_value=self.mock_resp
        ) as mock_post:
            record = self.client.create_record(
                display_name="New Home",
                record_type="household",
                city="Brussels",
                postal_code="1000",
                country="bE",
                category="dwelling",
            )
            assert isinstance(record, Record)
            params = kwargs_params(mock_post)
            assert params["displayName"] == "New Home"
            assert params["recordType"] == "household"
            assert params["postalCode"] == "1000"

    def test_create_record_with_auxiliaryheatingon_fix(self):
        """Verify the typo fix: auxiliaryHeatingOn, not uxiliaryheatingon."""
        self.mock_resp.json.return_value = {"id": 999}
        with patch.object(
            self.client.session, "post", return_value=self.mock_resp
        ) as mock_post:
            self.client.create_record(
                display_name="Test",
                record_type="household",
                city="Brussels",
                postal_code="1000",
                country="bE",
                category="dwelling",
                auxiliary_heating_on=1,
            )
            params = kwargs_params(mock_post)
            assert "auxiliaryHeatingOn" in params
            assert "uxiliaryheatingon" not in params
            assert "uxiliaryHeatingOn" not in params

    def test_get_record_data(self):
        self.mock_resp.json.return_value = {"value": []}
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            self.client.get_record_data(
                123, "electricityImport", "2024-01-01", "2024-12-31"
            )
            url = mock_get.call_args[0][0]
            assert "records/123/data/electricityImport" in url

    def test_edit_record(self):
        self.mock_resp.json.return_value = {"id": 123}
        with patch.object(self.client.session, "put", return_value=self.mock_resp):
            record = self.client.edit_record(123, displayName="Updated")
            assert isinstance(record, Record)

    def test_delete_record(self):
        self.mock_resp.json.return_value = {}
        with patch.object(self.client.session, "delete", return_value=self.mock_resp):
            self.client.delete_record(123)

    def test_get_record_definitions(self):
        self.mock_resp.json.return_value = {"data": [{"name": "electricityImport"}]}
        with patch.object(self.client.session, "get", return_value=self.mock_resp):
            defs = self.client.get_record_definitions("EA-123")
            assert isinstance(defs, list)


# ── Search Tests ──────────────────────────────────────────────


class TestSearch:
    def setup_method(self):
        self.client = JSONClient(api_key="test-key")
        self.mock_resp = MagicMock()
        self.mock_resp.raise_for_status.return_value = None

    def test_search_groups(self):
        self.mock_resp.json.return_value = [{"id": "g1"}]
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            groups = self.client.search_groups(q="energy")
            assert all(isinstance(g, Group) for g in groups)
            assert "search/groups" in mock_get.call_args[0][0]

    def test_search_services(self):
        self.mock_resp.json.return_value = [{"id": "s1", "name": "Service"}]
        with patch.object(
            self.client.session, "get", return_value=self.mock_resp
        ) as mock_get:
            self.client.search_services(q="solar", top=50)
            assert "search/services" in mock_get.call_args[0][0]
            params = kwargs_params(mock_get)
            assert params["top"] == 50

    def test_search_cities(self):
        self.mock_resp.json.return_value = [{"id": "c1", "name": "Brussels"}]
        with patch.object(self.client.session, "get", return_value=self.mock_resp):
            self.client.search_cities("bE", "Brus")


# ── Transfer Tests ────────────────────────────────────────────


class TestTransfers:
    def setup_method(self):
        self.client = JSONClient(api_key="test-key")
        self.mock_resp = MagicMock()
        self.mock_resp.raise_for_status.return_value = None

    def test_create_transfer(self):
        self.mock_resp.json.return_value = {"id": "tr1"}
        with patch.object(
            self.client.session, "post", return_value=self.mock_resp
        ) as mock_post:
            self.client.create_transfer(
                "EA-123", "user@example.com", remarks="Please accept"
            )
            params = kwargs_params(mock_post)
            assert params["recordId"] == "EA-123"
            assert params["email"] == "user@example.com"
            assert params["remarks"] == "Please accept"

    def test_cancel_transfer(self):
        self.mock_resp.json.return_value = {}
        with patch.object(
            self.client.session, "delete", return_value=self.mock_resp
        ) as mock_del:
            self.client.cancel_transfer("tr1")
            assert "transfers/tr1" in mock_del.call_args[0][0]

    def test_accept_transfer(self):
        self.mock_resp.json.return_value = {}
        with patch.object(
            self.client.session, "put", return_value=self.mock_resp
        ) as mock_put:
            self.client.accept_transfer("tr1")
            assert "transfers/tr1/accept" in mock_put.call_args[0][0]

    def test_decline_transfer(self):
        self.mock_resp.json.return_value = {}
        with patch.object(
            self.client.session, "put", return_value=self.mock_resp
        ) as mock_put:
            self.client.decline_transfer("tr1")
            assert "transfers/tr1/decline" in mock_put.call_args[0][0]


# ── Helper ────────────────────────────────────────────────────


def kwargs_params(mock_call):
    """Extract the params dict from a mock call."""
    _, kwargs = mock_call.call_args
    return kwargs.get("params", {})
