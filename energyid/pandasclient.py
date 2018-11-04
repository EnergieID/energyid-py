import pandas as pd

from .client import JSONClient


class PandasClient(JSONClient):
    def get_meter_readings(self, meter_id: str, **kwargs) -> pd.DataFrame:
        d = super(PandasClient, self).get_meter_readings(meter_id=meter_id, **kwargs)
        df = pd.DataFrame(d['readings'])
        df['timestamp'] = pd.DatetimeIndex(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        return df

    def get_record_data(self, record_id: int, theme: str, dataset: str, **kwargs) -> pd.Series:
        d = super(PandasClient, self).get_record_data(record_id=record_id, theme=theme, dataset=dataset, **kwargs)
        df = pd.DataFrame(d)
        df['key'] = pd.DatetimeIndex(df['key'])
        df.set_index('key', inplace=True)
        df.sort_index(inplace=True)
        ts = df['value']
        ts.index.name = None
        ts.name = dataset
        return ts