from typing import TYPE_CHECKING
from json import JSONDecodeError

from .misc import handle_skip_take_limit

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
    async def get_groups(self, filter="all") -> list["Group"]:
        return await self.client.get_member_groups(user_id=self.id, filter=filter)

    async def get_records(self) -> list["Record"]:
        return await self.client.get_member_records(user_id=self.id)

    async def get_limits(self) -> list[dict]:
        return await self.client.get_member_limits(user_id=self.id)

    async def update_profile(
        self, full_name: str, initials: str, biography: str = None
    ) -> None:
        result = await self.client.update_member(
            user_id=self.id,
            full_name=full_name,
            initials=initials,
            biography=biography,
        )
        dict.update(self, result)

    async def set_language(self, lang: str) -> None:
        result = await self.client.set_member_language(user_id=self.id, lang=lang)
        dict.update(self, result)


class Meter(Model):
    async def create_reading(self, timestamp: str, value: int | float) -> dict:
        return await self.client.create_meter_reading(
            meter_id=self.id, timestamp=timestamp, value=value
        )

    async def hide(self, hidden: bool = True) -> None:
        await self.client.hide_meter(meter_id=self.id, hidden=hidden)
        dict.update(self, {"hidden": hidden})

    async def close(self, closed: bool = True) -> None:
        await self.client.close_meter(meter_id=self.id, closed=closed)
        dict.update(self, {"closed": closed})

    async def edit(self, **kwargs) -> None:
        await self.client.edit_meter(meter_id=self.id, **kwargs)

    async def get_readings(self, **kwargs) -> dict:
        return await self.client.get_meter_readings(meter_id=self.id, **kwargs)

    async def get_reading(self, key: str) -> dict:
        return await self.client.get_meter_reading(meter_id=self.id, key=key)

    async def get_data(self, **kwargs):
        return await self.client.get_meter_data(meter_id=self.id, **kwargs)

    async def get_latest_reading(self) -> dict:
        try:
            return await self.client.get_meter_latest_reading(meter_id=self.id)
        except JSONDecodeError:
            return {}

    async def edit_reading(self, key: str, new_value: int | float) -> None:
        await self.client.edit_meter_reading(
            meter_id=self.id, key=key, new_value=new_value
        )

    async def edit_reading_status(self, key: str, new_status: str) -> None:
        await self.client.edit_meter_reading_status(
            meter_id=self.id, key=key, new_status=new_status
        )

    async def ignore_meter_reading(self, key: str, ignore: bool = True) -> None:
        await self.client.ignore_meter_reading(meter_id=self.id, key=key, ignore=ignore)

    async def delete(self) -> None:
        await self.client.delete_meter(meter_id=self.id)

    async def delete_reading(self, key: str) -> None:
        await self.client.delete_meter_reading(meter_id=self.id, key=key)


class Record(Model):
    @property
    def id(self) -> str | int:
        try:
            return super().id
        except KeyError:
            return self["recordId"]

    @property
    def timezone(self) -> str:
        return self["timeZone"]

    @property
    def number(self) -> str:
        return self["recordNumber"]

    async def extend_info(self):
        record = await self.client.get_record(record_id=self.id)
        dict.update(self, record)

    async def get_meters(self, **kwargs) -> list[Meter]:
        return await self.client.get_record_meters(record_id=self.id, **kwargs)

    async def get_groups(self) -> list["Group"]:
        return await self.client.get_record_groups(record_id=self.id)

    async def get_data(self, name: str, start: str, end: str, **kwargs) -> dict:
        return await self.client.get_record_data(
            record_id=self.id, name=name, start=start, end=end, **kwargs
        )

    async def edit(self, **kwargs) -> None:
        await self.client.edit_record(record_id=self.id, **kwargs)

    async def delete(self) -> None:
        await self.client.delete_record(record_id=self.id)

    async def create_meter(
        self, display_name: str, metric: str, unit: str, reading_type: str, **kwargs
    ) -> Meter:
        return await self.client.create_meter(
            record_id=self.id,
            display_name=display_name,
            metric=metric,
            unit=unit,
            reading_type=reading_type,
            **kwargs,
        )

    async def get_definitions(self) -> list[dict]:
        return await self.client.get_record_definitions(record_id=self.id)

    async def get_directives(self) -> list[dict]:
        return await self.client.get_record_directives(record_id=self.id)

    async def get_activity(self, **kwargs) -> dict:
        return await self.client.get_record_activity(record_id=self.id, **kwargs)

    async def get_timeline(self, from_date: str, to_date: str) -> list[dict]:
        return await self.client.get_record_timeline(
            record_id=self.id, from_date=from_date, to_date=to_date
        )

    async def create_timeline_item(
        self, display_name: str, start: str, **kwargs
    ) -> dict:
        return await self.client.create_timeline_item(
            record_id=self.id, display_name=display_name, start=start, **kwargs
        )

    async def get_limits(self) -> list[dict]:
        return await self.client.get_record_limits(record_id=self.id)

    async def get_benchmark(
        self, name: str, year: int, month: int | None = None
    ) -> dict:
        return await self.client.get_record_benchmark(
            record_id=self.id, name=name, year=year, month=month
        )

    async def add_to_group(self, group_id: str, access_key: str | None = None) -> None:
        await self.client.add_record_to_group(
            group_id=group_id, record_id=self.id, access_key=access_key
        )

    async def remove_from_group(self, group_id: str) -> None:
        await self.client.remove_record_from_group(group_id=group_id, record_id=self.id)


class Group(Model):
    async def get_records(self, amount: int | None = None, chunk_size=200, **kwargs):
        if amount is None:
            amount = self.get("recordCount")
        if amount is not None:
            async for record in handle_skip_take_limit(
                self.client.get_group_records,
                group_id=self.id,
                amount=amount,
                chunk_size=chunk_size,
                **kwargs,
            ):
                yield record
        else:
            # Fallback: single request
            records = await self.client.get_group_records(group_id=self.id, **kwargs)
            for r in records:
                yield r

    async def get_members(self, amount: int | None = None, chunk_size=200):
        if amount is not None:
            async for member in handle_skip_take_limit(
                self.client.get_group_members,
                group_id=self.id,
                amount=amount,
                chunk_size=chunk_size,
            ):
                yield member
        else:
            members = await self.client.get_group_members(group_id=self.id)
            for m in members:
                yield m

    async def get_meters(self, amount: int | None = None, chunk_size=200, **kwargs):
        if amount is not None:
            async for meter in handle_skip_take_limit(
                self.client.get_group_meters,
                group_id=self.id,
                amount=amount,
                chunk_size=chunk_size,
                **kwargs,
            ):
                yield meter
        else:
            meters = await self.client.get_group_meters(group_id=self.id, **kwargs)
            for m in meters:
                yield m

    async def get_my_records(self, **kwargs) -> list[Record]:
        return await self.client.get_group_my_records(group_id=self.id, **kwargs)

    async def get_admins(self) -> list[dict]:
        return await self.client.get_group_admins(group_id=self.id)

    async def add_record(self, record_id: int, access_key: str | None = None) -> None:
        await self.client.add_record_to_group(
            group_id=self.id, record_id=record_id, access_key=access_key
        )

    async def remove_record(self, record_id: int) -> None:
        await self.client.remove_record_from_group(
            group_id=self.id, record_id=record_id
        )


class Organization(Model):
    async def get_groups(self, lang: str | None = None) -> list[Group]:
        return await self.client.get_organization_groups(org_id=self.id, lang=lang)
