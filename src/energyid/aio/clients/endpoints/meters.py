import asyncio

import pandas as pd

from ...models import Meter
from ..data_helpers import build_meter_data_calls


class MetersMixin:
    async def get_meter(self, meter_id: str) -> Meter:
        endpoint = f"meters/{meter_id}"
        d = await self._request("GET", endpoint)
        return Meter(d, client=self)

    async def get_meter_readings(
        self,
        meter_id: str,
        take: int = 1000,
        nextRowKey: str | None = None,
        **kwargs,
    ) -> dict:
        endpoint = f"meters/{meter_id}/readings"
        return await self._request(
            "GET", endpoint, take=take, nextRowKey=nextRowKey, **kwargs
        )

    async def get_meter_latest_reading(self, meter_id: str) -> dict:
        endpoint = f"meters/{meter_id}/readings/latest"
        return await self._request("GET", endpoint)

    async def create_meter_reading(
        self, meter_id: str, value: int | float, timestamp: str
    ) -> dict:
        endpoint = f"meters/{meter_id}/readings"
        return await self._request("POST", endpoint, value=value, timestamp=timestamp)

    async def _create_meter(self, **kwargs) -> Meter:
        d = await self._request("POST", "meters", **kwargs)
        return Meter(d, client=self)

    async def create_meter(
        self,
        record_id: str,
        display_name: str,
        metric: str,
        unit: str,
        reading_type: str,
        **kwargs,
    ) -> Meter:
        return await self._create_meter(
            recordId=record_id,
            displayName=display_name,
            metric=metric,
            unit=unit,
            readingType=reading_type,
            **kwargs,
        )

    async def hide_meter(self, meter_id: str, hidden: bool = True) -> Meter:
        endpoint = f"meters/{meter_id}/hidden"
        d = await self._request("POST", endpoint, hidden=hidden)
        return Meter(d, client=self)

    async def close_meter(self, meter_id: str, closed: bool = True) -> dict:
        endpoint = f"meters/{meter_id}/closed"
        return await self._request("PUT", endpoint, value=closed)

    async def edit_meter(self, meter_id: str, **kwargs) -> Meter:
        endpoint = f"meters/{meter_id}"
        d = await self._request("PUT", endpoint, **kwargs)
        return Meter(d, client=self)

    @staticmethod
    def _get_meter_data_kwargs(
        meter_id: str,
        start: str | pd.Timestamp | None = None,
        end: str | pd.Timestamp | None = None,
        interval: str = "P1D",
    ) -> list[dict]:
        return build_meter_data_calls(
            meter_id=meter_id, start=start, end=end, interval=interval
        )

    async def get_meter_data(
        self,
        meter_id: str,
        start: str | pd.Timestamp | None = None,
        end: str | pd.Timestamp | None = None,
        interval: str = "P1D",
    ) -> list[dict]:
        calls = self._get_meter_data_kwargs(
            meter_id=meter_id, start=start, end=end, interval=interval
        )
        requests = [self._request(**call) for call in calls]
        return list(await asyncio.gather(*requests))

    async def get_meter_reading(self, meter_id: str, key: str) -> dict:
        endpoint = f"meters/{meter_id}/readings/{key}"
        return await self._request("GET", endpoint)

    async def edit_meter_reading(
        self, meter_id: str, key: str, new_value: int | float
    ) -> dict:
        endpoint = f"meters/{meter_id}/readings/{key}/value"
        return await self._request("PUT", endpoint, newValue=new_value)

    async def edit_meter_reading_status(
        self, meter_id: str, key: str, new_status: str
    ) -> dict:
        endpoint = f"meters/{meter_id}/readings/{key}/status"
        return await self._request("PUT", endpoint, statuscode=new_status)

    async def ignore_meter_reading(
        self, meter_id: str, key: str, ignore: bool = True
    ) -> dict:
        endpoint = f"meters/{meter_id}/readings/{key}/ignore"
        return await self._request("PUT", endpoint, ignore=ignore)

    async def delete_meter(self, meter_id: str) -> None:
        endpoint = f"meters/{meter_id}"
        await self._request("DELETE", endpoint)

    async def delete_meter_reading(self, meter_id: str, key: str) -> None:
        endpoint = f"meters/{meter_id}/readings/{key}"
        await self._request("DELETE", endpoint)
