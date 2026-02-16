from functools import wraps
import datetime as dt
from urllib.parse import quote

import aiohttp
import asyncio

import pandas as pd

import energyid
from energyid.client import Scope
from .models import Member, Record, Group, Meter, Organization


def authenticated(func):
    """
    Decorator to check if access token has expired.
    If it has, use the refresh token to request a new access token.
    Skipped entirely for API Key and Device Token auth.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        self = args[0]
        # API Key and Device Token auth don't need token management
        if self._auth_mode in ("api_key", "device_token"):
            return await func(*args, **kwargs)
        if self.token is None:
            async with self.auth_lock:
                if self.token is None:
                    if self._username is not None and self._password is not None:
                        await self.authenticate(
                            username=self._username,
                            password=self._password,
                            scopes=self._scopes,
                        )
                    else:
                        raise PermissionError(
                            "You haven't authenticated yet and "
                            "have not provided credentials!"
                        )
        if (
            self._refresh_token is not None
            and self._token_expiration_time <= dt.datetime.now(dt.timezone.utc)
        ):
            async with self.auth_lock:
                if (
                    self._refresh_token is not None
                    and self._token_expiration_time <= dt.datetime.now(dt.timezone.utc)
                ):
                    await self._re_authenticate()
        return await func(*args, **kwargs)

    return wrapper


class BaseClient:
    URL = "https://api.energyid.eu/api/v1"
    AUTH_URL = "https://identity.energyid.eu/connect/token"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        username: str | None = None,
        password: str | None = None,
        scopes: set[Scope] | None = (
            Scope.RECORDS_READ,
            Scope.PROFILE_READ,
            Scope.GROUPS_READ,
        ),
        session: aiohttp.ClientSession | None = None,
        api_key: str | None = None,
        device_token: str | None = None,
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self._username = username
        self._password = password
        self._scopes = scopes
        self._token = None
        self._refresh_token = None
        self._token_expiration_time = None
        self._session = session
        self._auth_lock: asyncio.Lock | None = None
        self._auth_headers = {}

        # Determine auth mode
        if api_key is not None:
            self._auth_mode = "api_key"
            self._auth_headers = {"Authorization": f"apiKey {api_key}"}
        elif device_token is not None:
            self._auth_mode = "device_token"
            self._auth_headers = {"Authorization": f"device {device_token}"}
        elif client_id is not None and client_secret is not None:
            self._auth_mode = "oauth2"
        else:
            raise ValueError(
                "You must provide either api_key, device_token, "
                "or client_id + client_secret for OAuth2 authentication."
            )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        if self._session is not None:
            await self._session.close()

    @property
    def auth_lock(self) -> asyncio.Lock:
        if self._auth_lock is None:
            self._auth_lock = asyncio.Lock()
        return self._auth_lock

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, value):
        self._token = value
        self._auth_headers = {"Authorization": f"Bearer {value}"}

    def _set_token_expiration_time(self, expires_in):
        self._token_expiration_time = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
            0, expires_in
        )

    def _auth_params(self, username: str, password: str, scopes: set[Scope]) -> dict:
        return {
            "grant_type": "password",
            "username": username,
            "password": password,
            "scope": " ".join(scope.value for scope in scopes) + " offline_access",
        }

    def _re_auth_params(self) -> dict:
        return {"grant_type": "refresh_token", "refresh_token": self._refresh_token}

    async def authenticate(
        self,
        username: str,
        password: str,
        scopes: set[Scope] = (
            Scope.RECORDS_READ,
            Scope.PROFILE_READ,
            Scope.GROUPS_READ,
        ),
    ):
        await self._auth_request(
            data=self._auth_params(username=username, password=password, scopes=scopes)
        )

    async def _re_authenticate(self):
        await self._auth_request(data=self._re_auth_params())

    async def _auth_request(self, data: dict):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data.update(
            {"client_id": self._client_id, "client_secret": self._client_secret}
        )
        async with self.session.post(
            url=self.AUTH_URL, data=data, headers=headers
        ) as r:
            r.raise_for_status()
            response = await r.json()
        self.token = response["access_token"]
        self._refresh_token = response.get("refresh_token")
        self._set_token_expiration_time(expires_in=response["expires_in"])

    @authenticated
    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        headers = {
            "Content-Type": "application/json",
            **self._auth_headers,
        }
        endpoint = quote(endpoint)
        url = f"{self.URL}/{endpoint}"
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        async with self.session.request(
            method=method, url=url, headers=headers, params=kwargs
        ) as r:
            r.raise_for_status()
            if method == "DELETE":
                return {}
            j = await r.json()
        return j


class JSONClient(BaseClient):
    # ── Catalogs ──────────────────────────────────────────────

    async def get_meter_catalog(self) -> dict:
        endpoint = "catalogs/meters"
        return await self._request("GET", endpoint)

    # ── Groups ────────────────────────────────────────────────

    async def get_group(self, group_id: str, **kwargs) -> Group:
        endpoint = f"groups/{group_id}"
        d = await self._request("GET", endpoint, **kwargs)
        return Group(d, client=self)

    async def get_group_records(
        self, group_id: str, take: int = 200, skip: int = 0, **kwargs
    ) -> list[Record]:
        endpoint = f"groups/{group_id}/records"
        d = await self._request("GET", endpoint, take=take, skip=skip, **kwargs)
        return [Record(r, client=self) for r in d]

    async def get_group_members(
        self, group_id: str, take: int = 200, skip: int = 0
    ) -> list[Member]:
        endpoint = f"groups/{group_id}/members"
        d = await self._request("GET", endpoint, take=take, skip=skip)
        return [Member(u, client=self) for u in d]

    async def get_group_meters(
        self, group_id: str, take: int = 200, skip: int = 0, **kwargs
    ) -> list[Meter]:
        endpoint = f"groups/{group_id}/meters"
        d = await self._request("GET", endpoint, take=take, skip=skip, **kwargs)
        return [Meter(m, client=self) for m in d]

    async def get_group_my_records(self, group_id: str, **kwargs) -> list[Record]:
        endpoint = f"groups/{group_id}/records/mine"
        d = await self._request("GET", endpoint, **kwargs)
        return [Record(r, client=self) for r in d]

    async def get_group_admins(self, group_id: str) -> list[dict]:
        endpoint = f"groups/{group_id}/admins"
        return await self._request("GET", endpoint)

    async def add_record_to_group(
        self, group_id: str, record_id: int, access_key: str | None = None
    ) -> dict:
        endpoint = f"groups/{group_id}/records"
        return await self._request(
            "POST", endpoint, recordId=record_id, accessKey=access_key
        )

    async def change_reference_of_record_in_group(
        self, group_id: str, record_id: int, reference: str | None = None
    ) -> dict:
        endpoint = f"groups/{group_id}/records/{record_id}/reference"
        return await self._request("PUT", endpoint, reference=reference)

    async def remove_record_from_group(self, group_id: str, record_id: int) -> None:
        endpoint = f"groups/{group_id}/records/{record_id}"
        await self._request("DELETE", endpoint)

    # ── Members ───────────────────────────────────────────────

    async def get_member(self, user_id: str = "me") -> Member:
        endpoint = f"members/{user_id}"
        d = await self._request("GET", endpoint)
        return Member(d, client=self)

    async def update_member(
        self,
        user_id: str,
        full_name: str,
        initials: str,
        biography: str | None = None,
    ) -> Member:
        endpoint = f"members/{user_id}"
        d = await self._request(
            "PUT",
            endpoint,
            fullName=full_name,
            initials=initials,
            biography=biography,
        )
        return Member(d, client=self)

    async def get_member_limits(self, user_id: str = "me") -> list[dict]:
        endpoint = f"members/{user_id}/limits"
        return await self._request("GET", endpoint)

    async def set_member_language(self, user_id: str, lang: str) -> Member:
        endpoint = f"members/{user_id}/lang"
        d = await self._request("PUT", endpoint, lang=lang)
        return Member(d, client=self)

    async def set_member_default_record(self, user_id: str, record_id: str) -> Member:
        endpoint = f"members/{user_id}/defaultRecord"
        d = await self._request("PUT", endpoint, recordId=record_id)
        return Member(d, client=self)

    async def set_member_default_record_page(self, user_id: str, page: str) -> Member:
        endpoint = f"members/{user_id}/defaultRecordPage"
        d = await self._request("PUT", endpoint, page=page)
        return Member(d, client=self)

    async def get_member_groups(self, user_id: str = "me", **kwargs) -> list[Group]:
        endpoint = f"members/{user_id}/groups"
        d = await self._request("GET", endpoint, **kwargs)
        return [Group(g, client=self) for g in d]

    async def get_member_records(
        self,
        user_id: str = "me",
        filter: str | None = None,
        accessLevel: str | None = None,
        expand: str | None = None,
    ) -> list[Record]:
        endpoint = f"members/{user_id}/records"
        d = await self._request(
            "GET",
            endpoint,
            filter=filter,
            accessLevel=accessLevel,
            expand=expand,
        )
        return [Record(r, client=self) for r in d]

    # ── Meters ────────────────────────────────────────────────

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
        endpoint = "meters"
        d = await self._request("POST", endpoint, **kwargs)
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
        meter = await self._create_meter(
            recordId=record_id,
            displayName=display_name,
            metric=metric,
            unit=unit,
            readingType=reading_type,
            **kwargs,
        )
        return meter

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
        return energyid.client.JSONClient._get_meter_data_kwargs(
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
        resp = await asyncio.gather(*requests)
        return list(resp)

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

    # ── Organizations ─────────────────────────────────────────

    async def get_organization(self, org_id: str) -> Organization:
        endpoint = f"organizations/{org_id}"
        d = await self._request("GET", endpoint)
        return Organization(d, client=self)

    async def get_organization_groups(
        self, org_id: str, lang: str | None = None
    ) -> list[Group]:
        endpoint = f"organizations/{org_id}/groups"
        d = await self._request("GET", endpoint, lang=lang)
        return [Group(g, client=self) for g in d]

    # ── Records ───────────────────────────────────────────────

    async def get_record(self, record_id: int, **kwargs) -> Record:
        endpoint = f"records/{record_id}"
        d = await self._request("GET", endpoint, **kwargs)
        return Record(d, client=self)

    async def get_record_meters(
        self, record_id: int, filter: dict = None, **kwargs
    ) -> list[Meter]:
        endpoint = f"records/{record_id}/meters"
        d = await self._request("GET", endpoint, **kwargs)
        meters = [Meter(m, client=self) for m in d]
        if filter:
            for key in filter:
                meters = [meter for meter in meters if meter[key] == filter[key]]
        return meters

    async def get_record_groups(self, record_id: int, **kwargs) -> list[Group]:
        endpoint = f"records/{record_id}/groups"
        d = await self._request("GET", endpoint, **kwargs)
        return [Group(g, client=self) for g in d]

    async def get_record_data(
        self,
        record_id: int,
        name: str,
        start: str,
        end: str,
        interval: str = "day",
        filter: str = None,
        grouping: str = None,
        **kwargs,
    ) -> dict:
        endpoint = f"records/{record_id}/data/{name}"
        return await self._request(
            "GET",
            endpoint,
            start=start,
            end=end,
            filter=filter,
            interval=interval,
            grouping=grouping,
            **kwargs,
        )

    async def get_record_directives(self, record_id: str) -> list[dict]:
        endpoint = f"records/{record_id}/directives"
        return await self._request("GET", endpoint)

    async def get_record_directive_signals(
        self,
        record_id: str,
        directive_id: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict:
        endpoint = f"records/{record_id}/directives/{directive_id}"
        return await self._request("GET", endpoint, limit=limit, offset=offset)

    async def get_record_activity(
        self,
        record_id: str,
        take: int = 100,
        nextRowKey: str | None = None,
    ) -> dict:
        endpoint = f"records/{record_id}/activity"
        return await self._request("GET", endpoint, take=take, nextRowKey=nextRowKey)

    async def get_record_timeline(
        self, record_id: str, from_date: str, to_date: str
    ) -> list[dict]:
        endpoint = f"records/{record_id}/timeline"
        return await self._request(
            "GET", endpoint, **{"from": from_date, "to": to_date}
        )

    async def create_timeline_item(
        self,
        record_id: str,
        display_name: str,
        start: str,
        description: str | None = None,
        type: str | None = None,
        private: bool | None = None,
        categories: str | None = None,
        customCategory: str | None = None,
        metadata: str | None = None,
        end: str | None = None,
        projectId: str | None = None,
    ) -> dict:
        endpoint = f"records/{record_id}/timeline"
        return await self._request(
            "POST",
            endpoint,
            displayName=display_name,
            start=start,
            description=description,
            type=type,
            private=private,
            categories=categories,
            customCategory=customCategory,
            metadata=metadata,
            end=end,
            projectId=projectId,
        )

    async def update_timeline_item(
        self,
        record_id: str,
        item_id: str,
        display_name: str,
        start: str,
        description: str | None = None,
        categories: str | None = None,
        private: bool | None = None,
        metadata: str | None = None,
        end: str | None = None,
    ) -> dict:
        endpoint = f"records/{record_id}/timeline/{item_id}"
        return await self._request(
            "PUT",
            endpoint,
            displayName=display_name,
            start=start,
            description=description,
            categories=categories,
            private=private,
            metadata=metadata,
            end=end,
        )

    async def delete_timeline_item(self, record_id: str, item_id: str) -> None:
        endpoint = f"records/{record_id}/timeline/{item_id}"
        await self._request("DELETE", endpoint)

    async def get_record_limits(self, record_id: str) -> list[dict]:
        endpoint = f"records/{record_id}/limits"
        return await self._request("GET", endpoint)

    async def get_record_benchmark(
        self,
        record_id: str,
        name: str,
        year: int,
        month: int | None = None,
    ) -> dict:
        endpoint = f"records/{record_id}/benchmark/{name}"
        return await self._request("GET", endpoint, year=year, month=month)

    async def get_record_benchmark_filtered(
        self,
        record_id: str,
        name: str,
        filter: str,
        year: int,
        month: int | None = None,
    ) -> dict:
        endpoint = f"records/{record_id}/benchmark/{name}/{filter}"
        return await self._request("GET", endpoint, year=year, month=month)

    async def _create_record(self, **kwargs) -> Record:
        endpoint = "records"
        d = await self._request("POST", endpoint, **kwargs)
        return Record(d, client=self)

    async def create_record(
        self,
        display_name: str,
        record_type: str,
        city: str,
        postal_code: str,
        country: str,
        category: str,
        street_address: str | None = None,
        tags: list[str] | None = None,
        dwelling_type: int | None = None,
        occupants: int | None = None,
        principal_residence: bool | None = None,
        heating_on: int | None = None,
        auxiliary_heating_on: int | None = None,
        hot_water_on: int | None = None,
        cooking_on: int | None = None,
        occupier_type: int | None = None,
        floor_surface: float | None = None,
        year_of_construction: int | None = None,
        year_of_renovation: int | None = None,
        energy_performance: float | None = None,
        energy_rating: float | None = None,
        energy_efficiency: int | None = None,
        installations: str | None = None,
        workspace_id: str | None = None,
        **kwargs,
    ) -> Record:
        record = await self._create_record(
            displayName=display_name,
            recordType=record_type,
            city=city,
            postalCode=postal_code,
            country=country,
            category=category,
            streetAddress=street_address,
            tags=tags,
            dwellingType=dwelling_type,
            occupants=occupants,
            principalResidence=principal_residence,
            heatingOn=heating_on,
            auxiliaryHeatingOn=auxiliary_heating_on,
            hotWaterOn=hot_water_on,
            cookingOn=cooking_on,
            occupierType=occupier_type,
            floorSurface=floor_surface,
            yearOfConstruction=year_of_construction,
            yearOfRenovation=year_of_renovation,
            energyPerformance=energy_performance,
            energyRating=energy_rating,
            energyEfficiency=energy_efficiency,
            installations=installations,
            workspaceId=workspace_id,
            **kwargs,
        )
        return record

    async def edit_record(self, record_id: int, **kwargs) -> Record:
        endpoint = f"records/{record_id}"
        d = await self._request("PUT", endpoint, **kwargs)
        return Record(d, client=self)

    async def delete_record(self, record_id: int) -> None:
        endpoint = f"records/{record_id}"
        await self._request("DELETE", endpoint)

    async def get_record_definitions(self, record_id: str) -> list[dict]:
        endpoint = f"records/{record_id}/definitions"
        d = await self._request("GET", endpoint)
        return d["data"]

    # ── Search ────────────────────────────────────────────────

    async def search_groups(self, q: str = None, **kwargs) -> list[Group]:
        endpoint = "search/groups"
        d = await self._request("GET", endpoint, q=q, **kwargs)
        return [Group(g, client=self) for g in d]

    async def search_services(
        self, q: str = None, top: int = 100, skip: int = 0, **kwargs
    ) -> list[dict]:
        endpoint = "search/services"
        return await self._request("GET", endpoint, q=q, top=top, skip=skip, **kwargs)

    async def search_cities(self, country: str, query: str, **kwargs) -> dict:
        endpoint = "search/cities"
        return await self._request(
            "GET", endpoint, country=country, query=query, **kwargs
        )

    # ── Transfers ─────────────────────────────────────────────

    async def create_transfer(
        self, record_id: str, email: str, remarks: str | None = None
    ) -> dict:
        endpoint = "transfers"
        return await self._request(
            "POST", endpoint, recordId=record_id, email=email, remarks=remarks
        )

    async def cancel_transfer(self, transfer_id: str) -> None:
        endpoint = f"transfers/{transfer_id}"
        await self._request("DELETE", endpoint)

    async def accept_transfer(self, transfer_id: str) -> dict:
        endpoint = f"transfers/{transfer_id}/accept"
        return await self._request("PUT", endpoint)

    async def decline_transfer(self, transfer_id: str) -> dict:
        endpoint = f"transfers/{transfer_id}/decline"
        return await self._request("PUT", endpoint)


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
        return energyid.PandasClient._parse_meter_data(data=data, meter_id=meter_id)

    def _parse_meter_data_multiple(self, data: list[dict], meter_id: str) -> pd.Series:
        return energyid.PandasClient._parse_meter_data_multiple(
            self, data=data, meter_id=meter_id
        )

    async def get_meter_data(self, meter_id: str, **kwargs) -> pd.Series:
        d = await JSONClient.get_meter_data(self, meter_id=meter_id, **kwargs)
        ts = self._parse_meter_data_multiple(data=d, meter_id=meter_id)
        return ts

    def _parse_record_data(self, d, name):
        return energyid.PandasClient._parse_record_data(self, d, name)

    async def get_record_data(
        self, record_id: int, name, record=None, **kwargs
    ) -> pd.Series | pd.DataFrame:
        d = await JSONClient.get_record_data(
            self, record_id=record_id, name=name, **kwargs
        )
        data = self._parse_record_data(d, name)
        if record is None:
            record = await self.get_record(record_id=record_id)
        data = data.tz_convert(record.timezone)
        return data
