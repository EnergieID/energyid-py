from typing import Optional

import pandas as pd

from .models import Record
from .client import JSONClient


class PandasClient(JSONClient):
    def get_meter_readings(self, meter_id: str, **kwargs) -> pd.DataFrame:
        d = super(PandasClient, self).get_meter_readings(meter_id=meter_id, **kwargs)
        df = pd.DataFrame(d['readings'])
        df['timestamp'] = pd.DatetimeIndex(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        return df

    def get_meter_data(self, meter_id: str, **kwargs) -> pd.Series:
        d = super(PandasClient, self).get_meter_data(meter_id=meter_id, **kwargs)
        df = pd.DataFrame(d['data'])
        if df.empty:
            return pd.Series(name=meter_id)
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        if isinstance(df.squeeze(), pd.Series):
            df = df.squeeze().rename(meter_id)
        else:
            return pd.Series(name=meter_id)
        return df

    def get_record_data(
            self, record_id: int, name: str, start: str = None, end: str = None,
            interval: str = 'day', filter: str = None,
            record: Optional[Record] = None, **kwargs) -> pd.Series:
        d = super(PandasClient, self).get_record_data(
            record_id=record_id, name=name, start=start, end=end,
            interval=interval, filter=filter, **kwargs)
        if len(d['value'][0]['data']) == 0:
            return pd.Series(name=name)
        df = pd.DataFrame(d['value'][0]['data'])
        df.set_index('timestamp', inplace=True)
        # noinspection PyTypeChecker
        df.index = pd.to_datetime(df.index, utc=True)
        df.index = pd.DatetimeIndex(df.index)
        df.sort_index(inplace=True)

        if record is None:
            record = self.get_record(record_id=record_id)
        df = df.tz_convert(record.timezone)

        if isinstance(df.squeeze(), pd.Series):
            ts = df.squeeze()
        else:
            return pd.Series(name=name)
        ts.index.name = None
        ts.name = name
        return ts
