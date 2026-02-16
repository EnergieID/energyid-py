# energyid-py

Python client for the [EnergyID API](https://api.energyid.eu).
Synchronous, async, and pandas interfaces — covering records, meters, readings, groups, organizations, search, and more.

## Installation

```bash
pip install energyid-py
```

## Quick Start

```python
from energyid import JSONClient

client = JSONClient(api_key="YOUR_API_KEY")

member = client.get_member()
records = client.get_member_records()
record = records[0]

meters = record.get_meters()
readings = meters[0].get_readings(take=10)
```

### Authentication

```python
# API Key (recommended)
client = JSONClient(api_key="YOUR_API_KEY")

# Device Token
client = JSONClient(device_token="YOUR_DEVICE_TOKEN")

# OAuth2
client = JSONClient(
    client_id="ID", client_secret="SECRET",
    username="user@example.com", password="pass",
)
```

## Features

### Rich Model Objects

All API responses are wrapped in dict-subclass models (`Member`, `Record`, `Meter`, `Group`, `Organization`) that provide convenience methods while remaining fully dict-compatible:

```python
record = client.get_record(record_id=123)
record["displayName"]       # dict access
record.id                   # property shortcut
record.timezone             # "Europe/Brussels"

meters = record.get_meters()
meter = meters[0]
meter.get_readings(take=5)
meter.get_latest_reading()
meter.create_reading("2024-06-01", 12345)
```

### Records

```python
# Data & definitions
definitions = record.get_definitions()
data = record.get_data("electricityImport", "2024-01-01", "2024-12-31", interval="month")
benchmark = record.get_benchmark("electricityImport", year=2024)

# Activity, timeline, directives, limits
activity = record.get_activity(take=10)
timeline = record.get_timeline("2020-01-01", "2025-12-31")
directives = record.get_directives()
limits = record.get_limits()

# CRUD
new_record = client.create_record("My Home", "household", "Brussels", "1000", "bE", "dwelling")
record.edit(displayName="Updated Name")
record.delete()
```

### Meters

```python
meter = record.create_meter("Solar", "electricityExport", "kilowattHour", "counter")
meter.create_reading("2024-06-01", 12345)
meter.edit(displayName="Renamed")
meter.hide()
meter.close()
meter.delete()
```

### Groups & Organizations

```python
groups = record.get_groups()
group = client.get_group(groups[0].id)

for member in group.get_members(amount=100):
    print(member["fullName"])

for rec in group.get_records(amount=50):
    print(rec["displayName"])

org = client.get_organization("org-id")
org.get_groups()
```

### Search

```python
client.search_groups(q="solar")
client.search_services(q="Fluvius", top=5)
client.search_cities("bE", "Gent")
client.get_meter_catalog()
```

### Transfers

```python
client.create_transfer("EA-123", "newowner@example.com")
client.accept_transfer("transfer-id")
client.decline_transfer("transfer-id")
```

## PandasClient

Returns pandas DataFrames and Series instead of raw dicts:

```python
from energyid import PandasClient

pc = PandasClient(api_key="YOUR_API_KEY")

df = pc.get_meter_readings(meter_id="meter-id", take=100)
ts = pc.get_record_data(record_id=123, name="electricityImport",
                        start="2024-01-01", end="2024-12-31", interval="month")
```

## Async Client

Full async mirror of all endpoints using `aiohttp`:

```python
from energyid.aio.client import JSONClient as AsyncJSONClient

async with AsyncJSONClient(api_key="YOUR_API_KEY") as client:
    member = await client.get_member()
    records = await client.get_member_records()
    meters = await client.get_record_meters(records[0].id)
```

## Demo

See [Demo.ipynb](Demo.ipynb) for a complete walkthrough of all endpoints.

## API Documentation

- API: https://api.energyid.eu/
- Swagger spec: https://api.energyid.eu/api-reference/index.html

## License

MIT
