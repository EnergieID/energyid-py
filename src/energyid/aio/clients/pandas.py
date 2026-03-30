import pandas as pd

from .data_helpers import (
    parse_meter_data,
    parse_meter_data_multiple,
    parse_multiple_series,
    parse_multiple_values,
    parse_record_data,
    parse_single_series,
)
from .json import JSONClient


class PandasClient(JSONClient):
    async def get_meter_readings(self, meter_id: str, **kwargs) -> pd.DataFrame:
        d = await JSONClient.get_meter_readings(self, meter_id=meter_id, **kwargs)
        df = pd.DataFrame(d["readings"])
        if df.empty:
            return df
        df["timestamp"] = pd.DatetimeIndex(pd.to_datetime(df["timestamp"], utc=True))
        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)
        return df

    @staticmethod
    def _parse_meter_data(data: dict, meter_id: str) -> pd.Series:
        return parse_meter_data(data=data, meter_id=meter_id)

    def _parse_meter_data_multiple(self, data: list[dict], meter_id: str) -> pd.Series:
        return parse_meter_data_multiple(data=data, meter_id=meter_id)

    @staticmethod
    def _parse_single_series(d: dict, name: str | None = None) -> pd.Series:
        return parse_single_series(d=d, name=name)

    def _parse_multiple_series(
        self, d: list[dict], name: str | None = None
    ) -> pd.DataFrame:
        return parse_multiple_series(d=d, name=name)

    def _parse_multiple_values(self, d: list[dict]) -> pd.DataFrame:
        return parse_multiple_values(d=d)

    def _parse_record_data(self, d, name):
        return parse_record_data(d=d, name=name)

    async def get_meter_data(self, meter_id: str, **kwargs) -> pd.Series:
        d = await JSONClient.get_meter_data(self, meter_id=meter_id, **kwargs)
        return self._parse_meter_data_multiple(data=d, meter_id=meter_id)

    async def get_record_data(
        self, record_id: int, name, record=None, **kwargs
    ) -> pd.Series | pd.DataFrame:
        d = await JSONClient.get_record_data(
            self, record_id=record_id, name=name, **kwargs
        )
        data = self._parse_record_data(d, name)
        if record is None:
            record = await self.get_record(record_id=record_id)
        return data.tz_convert(record.timezone)
