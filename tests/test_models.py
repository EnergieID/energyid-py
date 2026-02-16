"""Tests for model classes."""

from unittest.mock import MagicMock

from energyid.models import Member, Meter, Record, Group, Organization, Model


class TestModel:
    def test_model_is_dict(self):
        m = Model({"key": "value"}, client=None)
        assert isinstance(m, dict)
        assert m["key"] == "value"

    def test_model_id(self):
        m = Model({"id": "abc"}, client=None)
        assert m.id == "abc"

    def test_model_stores_client(self):
        mock_client = MagicMock()
        m = Model({}, client=mock_client)
        assert m.client is mock_client


class TestMember:
    def setup_method(self):
        self.mock_client = MagicMock()
        self.member = Member(
            {"id": "user1", "fullName": "Test"}, client=self.mock_client
        )

    def test_get_groups_delegates(self):
        self.mock_client.get_member_groups.return_value = []
        self.member.get_groups()
        self.mock_client.get_member_groups.assert_called_once_with(
            user_id="user1", filter="all"
        )

    def test_get_records_delegates(self):
        self.mock_client.get_member_records.return_value = []
        self.member.get_records()
        self.mock_client.get_member_records.assert_called_once_with(user_id="user1")

    def test_get_limits_delegates(self):
        self.mock_client.get_member_limits.return_value = []
        self.member.get_limits()
        self.mock_client.get_member_limits.assert_called_once_with(user_id="user1")

    def test_set_language_delegates(self):
        self.mock_client.set_member_language.return_value = {
            "id": "user1",
            "lang": "nl",
        }
        self.member.set_language("nl")
        self.mock_client.set_member_language.assert_called_once_with(
            user_id="user1", lang="nl"
        )

    def test_update_with_dict_works_as_dict(self):
        """Member.update with a dict arg should behave like dict.update."""
        self.member.update({"newKey": "newVal"})
        assert self.member["newKey"] == "newVal"

    def test_update_with_names_calls_client(self):
        self.mock_client.update_member.return_value = {
            "id": "user1",
            "fullName": "New",
            "initials": "NN",
        }
        self.member.update(full_name="New", initials="NN")
        self.mock_client.update_member.assert_called_once()


class TestMeter:
    def setup_method(self):
        self.mock_client = MagicMock()
        self.meter = Meter(
            {"id": "meter1", "metric": "electricityImport"}, client=self.mock_client
        )

    def test_create_reading_delegates(self):
        self.mock_client.create_meter_reading.return_value = {}
        self.meter.create_reading("2024-01-01", 100)
        self.mock_client.create_meter_reading.assert_called_once_with(
            meter_id="meter1", timestamp="2024-01-01", value=100
        )

    def test_hide_delegates(self):
        self.mock_client.hide_meter.return_value = None
        self.meter.hide(True)
        self.mock_client.hide_meter.assert_called_once_with(
            meter_id="meter1", hidden=True
        )
        assert self.meter["hidden"] is True

    def test_close_delegates(self):
        self.mock_client.close_meter.return_value = None
        self.meter.close(True)
        self.mock_client.close_meter.assert_called_once_with(
            meter_id="meter1", closed=True
        )
        assert self.meter["closed"] is True

    def test_delete_delegates(self):
        self.meter.delete()
        self.mock_client.delete_meter.assert_called_once_with(meter_id="meter1")

    def test_get_readings_delegates(self):
        self.mock_client.get_meter_readings.return_value = {"readings": []}
        self.meter.get_readings(take=50)
        self.mock_client.get_meter_readings.assert_called_once_with(
            meter_id="meter1", take=50
        )

    def test_get_reading_delegates(self):
        self.mock_client.get_meter_reading.return_value = {"key": "k1", "value": 100}
        self.meter.get_reading("k1")
        self.mock_client.get_meter_reading.assert_called_once_with(
            meter_id="meter1", key="k1"
        )

    def test_get_data_delegates(self):
        self.mock_client.get_meter_data.return_value = [{"data": []}]
        self.meter.get_data(start="2024-01-01", end="2024-12-31")
        self.mock_client.get_meter_data.assert_called_once_with(
            meter_id="meter1", start="2024-01-01", end="2024-12-31"
        )

    def test_get_latest_reading_delegates(self):
        self.mock_client.get_meter_latest_reading.return_value = {
            "key": "k1",
            "value": 999,
        }
        result = self.meter.get_latest_reading()
        assert result["value"] == 999

    def test_get_latest_reading_handles_json_error(self):
        from json import JSONDecodeError

        self.mock_client.get_meter_latest_reading.side_effect = JSONDecodeError(
            "", "", 0
        )
        assert self.meter.get_latest_reading() == {}

    def test_edit_delegates(self):
        self.meter.edit(displayName="Renamed")
        self.mock_client.edit_meter.assert_called_once_with(
            meter_id="meter1", displayName="Renamed"
        )

    def test_edit_reading_delegates(self):
        self.meter.edit_reading("k1", 200)
        self.mock_client.edit_meter_reading.assert_called_once_with(
            meter_id="meter1", key="k1", new_value=200
        )

    def test_edit_reading_status_delegates(self):
        self.meter.edit_reading_status("k1", "verified")
        self.mock_client.edit_meter_reading_status.assert_called_once_with(
            meter_id="meter1", key="k1", new_status="verified"
        )

    def test_ignore_reading_delegates(self):
        self.meter.ignore_meter_reading("k1", ignore=True)
        self.mock_client.ignore_meter_reading.assert_called_once_with(
            meter_id="meter1", key="k1", ignore=True
        )

    def test_delete_reading_delegates(self):
        self.meter.delete_reading("k1")
        self.mock_client.delete_meter_reading.assert_called_once_with(
            meter_id="meter1", key="k1"
        )


class TestRecord:
    def setup_method(self):
        self.mock_client = MagicMock()
        self.record = Record(
            {
                "id": 123,
                "displayName": "Home",
                "timeZone": "Europe/Brussels",
                "recordNumber": "EA-123",
            },
            client=self.mock_client,
        )

    def test_id_property(self):
        assert self.record.id == 123

    def test_id_fallback_to_recordId(self):
        record = Record({"recordId": 456}, client=self.mock_client)
        assert record.id == 456

    def test_timezone_property(self):
        assert self.record.timezone == "Europe/Brussels"

    def test_number_property(self):
        assert self.record.number == "EA-123"

    def test_get_meters_delegates(self):
        self.mock_client.get_record_meters.return_value = []
        self.record.get_meters()
        self.mock_client.get_record_meters.assert_called_once_with(record_id=123)

    def test_get_groups_delegates(self):
        self.mock_client.get_record_groups.return_value = []
        self.record.get_groups()
        self.mock_client.get_record_groups.assert_called_once_with(record_id=123)

    def test_get_directives_delegates(self):
        self.mock_client.get_record_directives.return_value = []
        self.record.get_directives()
        self.mock_client.get_record_directives.assert_called_once_with(record_id=123)

    def test_get_activity_delegates(self):
        self.mock_client.get_record_activity.return_value = {}
        self.record.get_activity(take=50)
        self.mock_client.get_record_activity.assert_called_once_with(
            record_id=123, take=50
        )

    def test_get_timeline_delegates(self):
        self.mock_client.get_record_timeline.return_value = []
        self.record.get_timeline("2024-01-01", "2024-12-31")
        self.mock_client.get_record_timeline.assert_called_once_with(
            record_id=123, from_date="2024-01-01", to_date="2024-12-31"
        )

    def test_create_timeline_item_delegates(self):
        self.mock_client.create_timeline_item.return_value = {}
        self.record.create_timeline_item("Solar", "2024-06-01", type="investment")
        self.mock_client.create_timeline_item.assert_called_once_with(
            record_id=123, display_name="Solar", start="2024-06-01", type="investment"
        )

    def test_get_limits_delegates(self):
        self.mock_client.get_record_limits.return_value = []
        self.record.get_limits()
        self.mock_client.get_record_limits.assert_called_once_with(record_id=123)

    def test_get_benchmark_delegates(self):
        self.mock_client.get_record_benchmark.return_value = {}
        self.record.get_benchmark("electricityImport", 2024, month=6)
        self.mock_client.get_record_benchmark.assert_called_once_with(
            record_id=123, name="electricityImport", year=2024, month=6
        )

    def test_extend_info_delegates(self):
        self.mock_client.get_record.return_value = Record(
            {"id": 123, "extra": "data"}, client=self.mock_client
        )
        self.record.extend_info()
        self.mock_client.get_record.assert_called_once_with(record_id=123)
        assert self.record["extra"] == "data"

    def test_create_meter_delegates(self):
        self.mock_client.create_meter.return_value = Meter(
            {"id": "new"}, client=self.mock_client
        )
        self.record.create_meter(
            "Test Meter", "electricityImport", "kilowattHour", "counter"
        )
        self.mock_client.create_meter.assert_called_once_with(
            record_id=123,
            display_name="Test Meter",
            metric="electricityImport",
            unit="kilowattHour",
            reading_type="counter",
        )

    def test_delete_delegates(self):
        self.record.delete()
        self.mock_client.delete_record.assert_called_once_with(record_id=123)

    def test_add_to_group_delegates(self):
        self.record.add_to_group("grp1", access_key="key123")
        self.mock_client.add_record_to_group.assert_called_once_with(
            group_id="grp1", record_id=123, access_key="key123"
        )

    def test_change_reference_in_group_delegates(self):
        self.record.change_reference_in_group("grp1", reference="REF-001")
        self.mock_client.change_reference_of_record_in_group.assert_called_once_with(
            group_id="grp1", record_id=123, reference="REF-001"
        )

    def test_remove_from_group_delegates(self):
        self.record.remove_from_group("grp1")
        self.mock_client.remove_record_from_group.assert_called_once_with(
            group_id="grp1", record_id=123
        )

    def test_get_data_delegates(self):
        self.mock_client.get_record_data.return_value = {"value": []}
        self.record.get_data("electricityImport", "2024-01-01", "2024-12-31")
        self.mock_client.get_record_data.assert_called_once_with(
            record_id=123,
            name="electricityImport",
            start="2024-01-01",
            end="2024-12-31",
            interval="day",
            filter=None,
            grouping=None,
        )

    def test_edit_delegates(self):
        self.record.edit(displayName="Updated")
        self.mock_client.edit_record.assert_called_once_with(
            record_id=123, displayName="Updated"
        )

    def test_get_definitions_delegates(self):
        self.mock_client.get_record_definitions.return_value = [{"name": "energyUse"}]
        self.record.get_definitions()
        self.mock_client.get_record_definitions.assert_called_once_with(record_id=123)


class TestGroup:
    def setup_method(self):
        self.mock_client = MagicMock()
        self.group = Group({"id": "grp1", "recordCount": 5}, client=self.mock_client)

    def test_get_my_records_delegates(self):
        self.mock_client.get_group_my_records.return_value = []
        self.group.get_my_records()
        self.mock_client.get_group_my_records.assert_called_once_with(group_id="grp1")

    def test_get_admins_delegates(self):
        self.mock_client.get_group_admins.return_value = []
        self.group.get_admins()
        self.mock_client.get_group_admins.assert_called_once_with(group_id="grp1")

    def test_add_record_delegates(self):
        self.group.add_record(123)
        self.mock_client.add_record_to_group.assert_called_once_with(
            group_id="grp1", record_id=123, access_key=None
        )

    def test_remove_record_delegates(self):
        self.group.remove_record(123)
        self.mock_client.remove_record_from_group.assert_called_once_with(
            group_id="grp1", record_id=123
        )

    def test_get_members_generator(self):
        """get_members should return a generator that yields Member objects."""
        self.mock_client.get_group_members.return_value = [
            Member({"id": "u1"}, client=self.mock_client),
            Member({"id": "u2"}, client=self.mock_client),
        ]
        members = list(self.group.get_members(amount=2))
        assert len(members) == 2

    def test_get_records_generator(self):
        self.mock_client.get_group_records.return_value = [
            Record({"id": 1}, client=self.mock_client),
        ]
        records = list(self.group.get_records(amount=1))
        assert len(records) == 1

    def test_get_meters_generator(self):
        self.mock_client.get_group_meters.return_value = [
            Meter({"id": "m1"}, client=self.mock_client),
        ]
        meters = list(self.group.get_meters(amount=1))
        assert len(meters) == 1

    def test_change_reference_of_record_delegates(self):
        self.group.change_reference_of_record(123, reference="REF-001")
        self.mock_client.change_reference_of_record_in_group.assert_called_once_with(
            group_id="grp1", record_id=123, reference="REF-001"
        )


class TestOrganization:
    def setup_method(self):
        self.mock_client = MagicMock()
        self.org = Organization(
            {"id": "org1", "displayName": "Test Org"}, client=self.mock_client
        )

    def test_id(self):
        assert self.org.id == "org1"

    def test_get_groups_delegates(self):
        self.mock_client.get_organization_groups.return_value = []
        self.org.get_groups(lang="nl")
        self.mock_client.get_organization_groups.assert_called_once_with(
            org_id="org1", lang="nl"
        )
