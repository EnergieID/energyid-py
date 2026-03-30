# energyid-py

Async Python client for the [EnergyID API](https://api.energyid.eu).

## Installation

```bash
pip install energyid-py
```

## Quick Start

```python
import asyncio
from energyid import JSONClient


async def main():
    async with JSONClient(api_key="YOUR_API_KEY") as client:
        member = await client.get_member()
        records = await client.get_member_records()
        meters = await client.get_record_meters(records[0].id)
        readings = await client.get_meter_readings(meters[0].id, take=10)
        print(member["fullName"], len(readings["readings"]))


asyncio.run(main())
```

## Authentication

```python
from energyid import JSONClient

# API Key (recommended)
client = JSONClient(api_key="YOUR_API_KEY")

# Device Token
client = JSONClient(device_token="YOUR_DEVICE_TOKEN")

# OAuth2
client = JSONClient(
    client_id="ID",
    client_secret="SECRET",
    username="user@example.com",
    password="pass",
)
```

## Built-in Request Throttling

`JSONClient` includes two safeguards to reduce backend pressure:

- `max_concurrency`: max in-flight HTTP requests.
- `max_requests_per_window` + `rate_limit_window_seconds`: request-rate cap.

Defaults are conservative (`max_concurrency=10`, `max_requests_per_window=20`, `rate_limit_window_seconds=1.0`).

```python
client = JSONClient(
    api_key="YOUR_API_KEY",
    max_concurrency=5,
    max_requests_per_window=10,
    rate_limit_window_seconds=1.0,
)
```

Set `max_concurrency=None` and/or `max_requests_per_window=None` to disable a limiter.

## PandasClient

Use `PandasClient` for DataFrame/Series output:

```python
import asyncio
from energyid import PandasClient


async def main():
    async with PandasClient(api_key="YOUR_API_KEY") as client:
        df = await client.get_meter_readings(meter_id="meter-id", take=100)
        ts = await client.get_record_data(
            record_id=123,
            name="electricityImport",
            start="2024-01-01",
            end="2024-12-31",
            interval="month",
        )
        print(df.shape, ts.shape)


asyncio.run(main())
```

## API Documentation

- API: https://api.energyid.eu/
- Swagger: https://api.energyid.eu/api-reference/index.html

## License

MIT
