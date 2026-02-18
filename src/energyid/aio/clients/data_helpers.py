from itertools import pairwise

import pandas as pd


def build_meter_data_calls(
    meter_id: str,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
    interval: str = "P1D",
) -> list[dict]:
    base = dict(method="GET", endpoint=f"meters/{meter_id}/data")
    calls = []
    if start is not None and end is not None:
        start = pd.to_datetime(start)
        end = pd.to_datetime(end)

        freqs = {
            "PT5M": "2D",
            "PT15M": "7D",
            "PT1H": "31D",
            "P1D": "731D",
            "P7D": "3653D",
            "P1M": "3653D",
            "P1Y": "3653D",
        }
        dates = list(
            pd.date_range(start=start, end=end, freq=freqs[interval], normalize=True)
        )
        dates.append(end)
        for _start, _end in pairwise(dates):
            call = base.copy()
            call["start"] = _start.strftime("%Y-%m-%d")
            call["end"] = _end.strftime("%Y-%m-%d")
            call["interval"] = interval
            calls.append(call)
    else:
        calls.append(base)
    return calls


def parse_meter_data(data: dict, meter_id: str) -> pd.Series:
    df = pd.DataFrame(data["data"])
    if df.empty:
        return pd.Series(name=meter_id, dtype="float")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df.set_index("timestamp", inplace=True)
    df.sort_index(inplace=True)
    ts = df.squeeze(axis=1)
    ts = ts.rename(meter_id)
    return ts


def parse_meter_data_multiple(data: list[dict], meter_id: str) -> pd.Series:
    return pd.concat([parse_meter_data(data=d, meter_id=meter_id) for d in data])


def parse_single_series(d: dict, name: str | None = None) -> pd.Series:
    if len(d) == 0:
        return pd.Series(name=name, dtype="object")
    df = pd.DataFrame(d)
    df.set_index("timestamp", inplace=True)
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


def parse_multiple_series(d: list[dict], name: str | None = None) -> pd.DataFrame:
    series_list = []
    for series in d:
        ts = parse_single_series(series["data"], name=series["name"])
        if ts.empty:
            continue
        ts.name = (name, ts.name)
        series_list.append(ts)
    if len(series_list) == 0:
        return pd.DataFrame()
    return pd.concat(series_list, axis=1)


def parse_multiple_values(d: list[dict]) -> pd.DataFrame:
    values_list = []
    for values in d:
        name = values["name"]
        data = parse_multiple_series(values["series"], name=name)
        values_list.append(data)
    if len(values_list) == 0:
        return pd.DataFrame()
    return pd.concat(values_list, axis=1)


def parse_record_data(d: dict, name: str):
    if len(d["value"]) == 1:
        values = d["value"][0]

        if "data" in values:
            return parse_single_series(values["data"], name=name)
        if "series" in values:
            return parse_multiple_series(values["series"], name=name)
        raise ValueError("Data block not found")

    return parse_multiple_values(d["value"])
