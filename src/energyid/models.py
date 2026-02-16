from typing import TYPE_CHECKING

from collections.abc import Iterator
from json import JSONDecodeError
import pandas as pd

from energyid.misc import handle_skip_take_limit

if TYPE_CHECKING:
    from .client import JSONClient


class Model(dict):
    def __init__(self, *args, client=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.client: "JSONClient" = client

    @property
    def id(self) -> str | int:
        return self["id"]


class Member(Model):
    def get_groups(self, filter="all") -> list["Group"]:
        return self.client.get_member_groups(user_id=self.id, filter=filter)

    def get_records(self) -> list["Record"]:
        return self.client.get_member_records(user_id=self.id)

    def get_limits(self) -> list[dict]:
        """Get the limits for this member."""
        return self.client.get_member_limits(user_id=self.id)

    def update(
        self,
        full_name: str = None,
        initials: str = None,
        biography: str = None,
        **kwargs,
    ) -> None:
        """Update this member's profile. If called with a dict (from dict.update), delegate to dict."""
        if isinstance(full_name, dict):
            # Called as dict.update(other_dict)
            super().update(full_name)
            return
        if full_name is not None and initials is not None:
            result = self.client.update_member(
                user_id=self.id,
                full_name=full_name,
                initials=initials,
                biography=biography,
            )
            super().update(result)

    def set_language(self, lang: str) -> None:
        """Set this member's preferred language."""
        result = self.client.set_member_language(user_id=self.id, lang=lang)
        super().update(result)


class Meter(Model):
    def create_reading(self, timestamp: str, value: int | float) -> dict:
        return self.client.create_meter_reading(
            meter_id=self.id, timestamp=timestamp, value=value
        )

    def hide(self, hidden: bool = True) -> None:
        self.client.hide_meter(meter_id=self.id, hidden=hidden)
        super().update({"hidden": hidden})

    def close(self, closed: bool = True) -> None:
        """Close or reopen this meter."""
        self.client.close_meter(meter_id=self.id, closed=closed)
        super().update({"closed": closed})

    def edit(self, **kwargs) -> None:
        self.client.edit_meter(meter_id=self.id, **kwargs)

    def get_readings(self, **kwargs) -> dict:
        return self.client.get_meter_readings(meter_id=self.id, **kwargs)

    def get_reading(self, key: str) -> dict:
        return self.client.get_meter_reading(meter_id=self.id, key=key)

    def get_data(self, **kwargs):
        return self.client.get_meter_data(meter_id=self.id, **kwargs)

    def get_latest_reading(self) -> dict:
        try:
            return self.client.get_meter_latest_reading(meter_id=self.id)
        except JSONDecodeError:
            return {}

    def edit_reading(self, key: str, new_value: int | float) -> None:
        self.client.edit_meter_reading(meter_id=self.id, key=key, new_value=new_value)

    def edit_reading_status(self, key: str, new_status: str) -> None:
        self.client.edit_meter_reading_status(
            meter_id=self.id, key=key, new_status=new_status
        )

    def ignore_meter_reading(self, key: str, ignore: bool = True) -> None:
        self.client.ignore_meter_reading(meter_id=self.id, key=key, ignore=ignore)

    def delete(self) -> None:
        self.client.delete_meter(meter_id=self.id)

    def delete_reading(self, key: str) -> None:
        self.client.delete_meter_reading(meter_id=self.id, key=key)


class Record(Model):
    @property
    def id(self) -> str | int:
        try:
            return super().id
        except KeyError:
            return self["recordId"]

    @property
    def timezone(self) -> str:
        try:
            return self["timeZone"]
        except KeyError:
            self.extend_info()
            return self["timeZone"]

    @property
    def number(self) -> str:
        try:
            return self["recordNumber"]
        except KeyError:
            self.extend_info()
            return self["recordNumber"]

    def add_to_group(self, group_id: str, access_key: str | None = None) -> None:
        """group_id can also be the group slug"""
        self.client.add_record_to_group(
            group_id=group_id, record_id=self.id, access_key=access_key
        )

    def change_reference_in_group(
        self, group_id: str, reference: str | None = None
    ) -> None:
        """group_id can also be the group slug"""
        self.client.change_reference_of_record_in_group(
            group_id=group_id, record_id=self.id, reference=reference
        )

    def remove_from_group(self, group_id: str) -> None:
        """group_id can also be the group slug"""
        self.client.remove_record_from_group(group_id=group_id, record_id=self.id)

    def get_meters(self, **kwargs) -> list[Meter]:
        return self.client.get_record_meters(record_id=self.id, **kwargs)

    def get_groups(self) -> list["Group"]:
        return self.client.get_record_groups(record_id=self.id)

    def get_data(
        self,
        name: str,
        start: str,
        end: str,
        interval: str = "day",
        filter: str = None,
        grouping: str = None,
        **kwargs,
    ) -> dict:
        return self.client.get_record_data(
            record_id=self.id,
            name=name,
            start=start,
            end=end,
            interval=interval,
            filter=filter,
            grouping=grouping,
            **kwargs,
        )

    def edit(self, **kwargs) -> None:
        self.client.edit_record(record_id=self.id, **kwargs)

    def delete(self) -> None:
        self.client.delete_record(record_id=self.id)

    def create_meter(
        self, display_name: str, metric: str, unit: str, reading_type: str, **kwargs
    ) -> Meter:
        return self.client.create_meter(
            record_id=self.id,
            display_name=display_name,
            metric=metric,
            unit=unit,
            reading_type=reading_type,
            **kwargs,
        )

    def extend_info(self):
        """You might get a record with limited info. Use this to extend the info"""
        record = self.client.get_record(record_id=self.id)
        dict.update(self, record)

    def get_definitions(self) -> list[dict]:
        return self.client.get_record_definitions(record_id=self.id)

    def get_directives(self) -> list[dict]:
        """List all directives for this record."""
        return self.client.get_record_directives(record_id=self.id)

    def get_activity(self, **kwargs) -> dict:
        """Get this record's activity log entries."""
        return self.client.get_record_activity(record_id=self.id, **kwargs)

    def get_timeline(self, from_date: str, to_date: str) -> list[dict]:
        """List the timeline items of this record."""
        return self.client.get_record_timeline(
            record_id=self.id, from_date=from_date, to_date=to_date
        )

    def create_timeline_item(self, display_name: str, start: str, **kwargs) -> dict:
        """Create a new timeline item for this record."""
        return self.client.create_timeline_item(
            record_id=self.id, display_name=display_name, start=start, **kwargs
        )

    def get_limits(self) -> list[dict]:
        """List the limits for this record."""
        return self.client.get_record_limits(record_id=self.id)

    def get_benchmark(self, name: str, year: int, month: int | None = None) -> dict:
        """Benchmark aggregated metrics for this record."""
        return self.client.get_record_benchmark(
            record_id=self.id, name=name, year=year, month=month
        )


class Group(Model):
    def get_members(
        self, amount: int | None = None, chunk_size=200
    ) -> Iterator[Member]:
        """Use amount=None to get all members"""
        members = handle_skip_take_limit(
            self.client.get_group_members,
            group_id=self.id,
            amount=amount,
            chunk_size=chunk_size,
        )
        return members

    def get_records(
        self, amount: int | None = None, chunk_size=200, **kwargs
    ) -> Iterator[Record]:
        """Use amount=None to get all records"""
        records = handle_skip_take_limit(
            self.client.get_group_records,
            group_id=self.id,
            amount=amount,
            chunk_size=chunk_size,
            **kwargs,
        )
        return records

    def get_meters(
        self, amount: int | None = None, chunk_size=200, **kwargs
    ) -> Iterator[Meter]:
        """Use amount=None to get all meters."""
        meters = handle_skip_take_limit(
            self.client.get_group_meters,
            group_id=self.id,
            amount=amount,
            chunk_size=chunk_size,
            **kwargs,
        )
        return meters

    def get_my_records(self, **kwargs) -> list[Record]:
        """Get my records in this group."""
        return self.client.get_group_my_records(group_id=self.id, **kwargs)

    def get_admins(self) -> list[dict]:
        """Get this group's admins."""
        return self.client.get_group_admins(group_id=self.id)

    def add_record(self, record_id: int, access_key: str | None = None) -> None:
        self.client.add_record_to_group(
            group_id=self.id, record_id=record_id, access_key=access_key
        )

    def change_reference_of_record(
        self, record_id: int, reference: str | None = None
    ) -> None:
        self.client.change_reference_of_record_in_group(
            group_id=self.id, record_id=record_id, reference=reference
        )

    def remove_record(self, record_id: int) -> None:
        self.client.remove_record_from_group(group_id=self.id, record_id=record_id)

    def get_individual_data(
        self,
        name: str,
        start: str,
        end: str,
        interval: str = "day",
        filter: str = None,
        **kwargs,
    ):
        def _gen_data():
            for record in self.get_records(**kwargs):
                data = record.get_data(
                    name=name,
                    start=start,
                    end=end,
                    interval=interval,
                    filter=filter,
                    **kwargs,
                )
                if data.empty:
                    continue

                if isinstance(data, pd.Series):
                    data.name = record.number
                else:  # pd.DataFrame
                    data.columns.set_levels([record.number], level=0, inplace=True)
                yield data

        data = _gen_data()
        df = pd.concat(data, axis=1)
        return df

    def get_records_dataframe(self, amount: int | None = None) -> pd.DataFrame:
        records = self.get_records(amount=amount)
        record_list = []
        for record in records:
            record.extend_info()
            record_list.append(record)
        df = pd.DataFrame.from_dict(record_list)
        return df


class Organization(Model):
    """Model representing an EnergyID organization."""

    def get_groups(self, lang: str | None = None) -> list[Group]:
        """List the groups of this organization."""
        return self.client.get_organization_groups(org_id=self.id, lang=lang)
