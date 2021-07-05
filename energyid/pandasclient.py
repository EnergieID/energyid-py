from typing import Optional, Dict, Union, List

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
            self, record_id: int, name: str, start: str, end: str,
            interval: str = 'day', filter: str = None,
            record: Optional[Record] = None,
            **kwargs) -> Union[pd.Series, pd.DataFrame]:
        d = super(PandasClient, self).get_record_data(
            record_id=record_id, name=name, start=start, end=end,
            interval=interval, filter=filter, **kwargs)
        if len(d['value']) == 1:
            values = d['value'][0]

            if 'data' in values:
                # single column
                data = self._parse_single_series(values['data'], name=name)
            elif 'series' in values:
                data = self._parse_multiple_series(values['series'], name=name)
            else:
                raise ValueError('Data block not found')
        else:
            data = self._parse_multiple_values(d['value'])

        if record is None:
            record = self.get_record(record_id=record_id)
        data = data.tz_convert(record.timezone)

        return data

    @staticmethod
    def _parse_single_series(d: Dict, name: Optional[str] = None) -> pd.Series:
        if len(d) == 0:
            return pd.Series(name=name)
        df = pd.DataFrame(d)
        df.set_index('timestamp', inplace=True)
        # noinspection PyTypeChecker
        df.index = pd.to_datetime(df.index, utc=True)
        df.index = pd.DatetimeIndex(df.index)
        df.sort_index(inplace=True)

        if isinstance(df.squeeze(), pd.Series):
            ts = df.squeeze()
        else:
            return pd.Series(name=name)
        ts.index.name = None
        ts.name = name
        return ts

    def _parse_multiple_series(self, d: List[Dict],
                               name: Optional[str] = None) -> pd.DataFrame:
        series_list = []
        for series in d:
            ts = self._parse_single_series(series['data'], name=series['name'])
            if ts.empty:
                continue
            ts.name = (name, ts.name)
            series_list.append(ts)
        if len(series_list) == 0:
            return pd.DataFrame()
        df = pd.concat(series_list, axis=1)
        return df

    def _parse_multiple_values(self, d: List[Dict]) -> pd.DataFrame:
        values_list = []
        for values in d:
            name = values['name']
            data = self._parse_multiple_series(values['series'], name=name)
            values_list.append(data)
        if len(values_list) == 0:
            return pd.DataFrame()
        df = pd.concat(values_list, axis=1)
        return df
