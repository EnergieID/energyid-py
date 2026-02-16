from enum import Enum
from functools import wraps
from itertools import pairwise

import pandas as pd
import requests
from urllib.parse import quote
import datetime as dt

from .models import Group, Record, Member, Meter, Organization


class Scope(Enum):
    RECORDS_WRITE = "records:write"
    RECORDS_READ = "records:read"
    PROFILE_WRITE = "profile:write"
    PROFILE_READ = "profile:read"
    GROUPS_WRITE = "groups:write"
    GROUPS_READ = "groups:read"


def authenticated(func):
    """
    Decorator to check if access token has expired.
    If it has, use the refresh token to request a new access token.
    Skipped entirely for API Key and Device Token auth.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        # API Key and Device Token auth don't need token management
        if self._auth_mode in ("api_key", "device_token"):
            return func(*args, **kwargs)
        if self.token is None:
            if self._username is not None and self._password is not None:
                self.authenticate(
                    username=self._username,
                    password=self._password,
                    scopes=self._scopes,
                )
            else:
                raise PermissionError(
                    "You haven't authenticated yet and have not provided credentials!"
                )
        if (
            self._refresh_token is not None
            and self._token_expiration_time <= dt.datetime.now(dt.timezone.utc)
        ):
            self._re_authenticate()
        return func(*args, **kwargs)

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
        session: requests.Session | None = None,
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

        # Determine auth mode
        if api_key is not None:
            self._auth_mode = "api_key"
            self._api_key = api_key
        elif device_token is not None:
            self._auth_mode = "device_token"
            self._device_token = device_token
        elif client_id is not None and client_secret is not None:
            self._auth_mode = "oauth2"
        else:
            raise ValueError(
                "You must provide either api_key, device_token, "
                "or client_id + client_secret for OAuth2 authentication."
            )

        # Set auth headers immediately for non-OAuth methods
        if self._auth_mode == "api_key":
            self.session.headers.update({"Authorization": f"apiKey {self._api_key}"})
        elif self._auth_mode == "device_token":
            self.session.headers.update(
                {"Authorization": f"device {self._device_token}"}
            )

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def _auth_params(self, username: str, password: str, scopes: set[Scope]) -> dict:
        return {
            "grant_type": "password",
            "username": username,
            "password": password,
            "scope": " ".join(scope.value for scope in scopes) + " offline_access",
        }

    def authenticate(
        self,
        username: str,
        password: str,
        scopes: set[Scope] = (
            Scope.RECORDS_READ,
            Scope.PROFILE_READ,
            Scope.GROUPS_READ,
        ),
    ):
        self._auth_request(
            data=self._auth_params(username=username, password=password, scopes=scopes)
        )

    def _re_auth_params(self) -> dict:
        return {"grant_type": "refresh_token", "refresh_token": self._refresh_token}

    def _re_authenticate(self):
        self._auth_request(data=self._re_auth_params())

    def _auth_request(self, data: dict):
        self.session.headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data.update(
            {"client_id": self._client_id, "client_secret": self._client_secret}
        )
        r = self.session.post(url=self.AUTH_URL, data=data)
        r.raise_for_status()
        response = r.json()
        self.token = response["access_token"]
        self._refresh_token = response.get("refresh_token")
        self._set_token_expiration_time(expires_in=response["expires_in"])

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, value):
        self._token = value
        self.session.headers.update({"Authorization": f"Bearer {value}"})

    def _set_token_expiration_time(self, expires_in):
        self._token_expiration_time = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
            0, expires_in
        )  # timedelta(days, seconds)

    @authenticated
    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        self.session.headers.update({"Content-Type": "application/json"})
        endpoint = quote(endpoint)
        url = f"{self.URL}/{endpoint}"
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if method == "GET":
            r = self.session.get(url, params=kwargs)
        elif method == "POST":
            r = self.session.post(url, params=kwargs)
        elif method == "PUT":
            r = self.session.put(url, params=kwargs)
        elif method == "DELETE":
            r = self.session.delete(url, params=kwargs)
            r.raise_for_status()
            return {}
        else:
            raise ValueError(f"Unknown method: {method}")
        r.raise_for_status()
        j = r.json()
        return j


class JSONClient(BaseClient):
    # ── Catalogs ──────────────────────────────────────────────

    def get_meter_catalog(self) -> dict:
        endpoint = "catalogs/meters"
        return self._request("GET", endpoint)

    # ── Groups ────────────────────────────────────────────────

    def get_group(self, group_id: str, **kwargs) -> Group:
        """group_id can also be the group slug"""
        endpoint = f"groups/{group_id}"
        d = self._request("GET", endpoint, **kwargs)
        return Group(d, client=self)

    def get_group_records(
        self, group_id: str, take: int = 200, skip: int = 0, **kwargs
    ) -> list[Record]:
        """group_id can also be the group slug"""
        endpoint = f"groups/{group_id}/records"
        d = self._request("GET", endpoint, take=take, skip=skip, **kwargs)
        return [Record(r, client=self) for r in d]

    def get_group_members(
        self, group_id: str, take: int = 200, skip: int = 0
    ) -> list[Member]:
        """group_id can also be the group slug"""
        endpoint = f"groups/{group_id}/members"
        d = self._request("GET", endpoint, take=take, skip=skip)
        return [Member(u, client=self) for u in d]

    def get_group_meters(
        self, group_id: str, take: int = 200, skip: int = 0, **kwargs
    ) -> list[Meter]:
        """Get a group's meters. group_id can also be the group slug."""
        endpoint = f"groups/{group_id}/meters"
        d = self._request("GET", endpoint, take=take, skip=skip, **kwargs)
        return [Meter(m, client=self) for m in d]

    def get_group_my_records(self, group_id: str, **kwargs) -> list[Record]:
        """Get my records in this group. group_id can also be the group slug."""
        endpoint = f"groups/{group_id}/records/mine"
        d = self._request("GET", endpoint, **kwargs)
        return [Record(r, client=self) for r in d]

    def get_group_admins(self, group_id: str) -> list[dict]:
        """Get a group's admins. group_id can also be the group slug."""
        endpoint = f"groups/{group_id}/admins"
        return self._request("GET", endpoint)

    def add_record_to_group(
        self, group_id: str, record_id: int, access_key: str | None = None
    ) -> dict:
        """group_id can also be the group slug"""
        endpoint = f"groups/{group_id}/records"
        return self._request("POST", endpoint, recordId=record_id, accessKey=access_key)

    def change_reference_of_record_in_group(
        self, group_id: str, record_id: int, reference: str | None = None
    ) -> dict:
        """group_id can also be the group slug"""
        endpoint = f"groups/{group_id}/records/{record_id}/reference"
        return self._request("PUT", endpoint, reference=reference)

    def remove_record_from_group(self, group_id: str, record_id: int) -> None:
        """group_id can also be the group slug"""
        endpoint = f"groups/{group_id}/records/{record_id}"
        self._request("DELETE", endpoint)

    # ── Members ───────────────────────────────────────────────

    @staticmethod
    def _get_member_kwargs(user_id: str = "me") -> dict:
        return dict(method="GET", endpoint=f"members/{user_id}")

    def get_member(self, user_id: str = "me") -> Member:
        """user_id can also be an e-mail address or simply 'me'"""
        d = self._request(**self._get_member_kwargs(user_id=user_id))
        return Member(d, client=self)

    def update_member(
        self,
        user_id: str,
        full_name: str,
        initials: str,
        biography: str | None = None,
    ) -> Member:
        """Update a member's profile."""
        endpoint = f"members/{user_id}"
        d = self._request(
            "PUT",
            endpoint,
            fullName=full_name,
            initials=initials,
            biography=biography,
        )
        return Member(d, client=self)

    def get_member_limits(self, user_id: str = "me") -> list[dict]:
        """List the limits for a user."""
        endpoint = f"members/{user_id}/limits"
        return self._request("GET", endpoint)

    def set_member_language(self, user_id: str, lang: str) -> Member:
        """Set a member's preferred language."""
        endpoint = f"members/{user_id}/lang"
        d = self._request("PUT", endpoint, lang=lang)
        return Member(d, client=self)

    def set_member_default_record(self, user_id: str, record_id: str) -> Member:
        """Set a member's default record."""
        endpoint = f"members/{user_id}/defaultRecord"
        d = self._request("PUT", endpoint, recordId=record_id)
        return Member(d, client=self)

    def set_member_default_record_page(self, user_id: str, page: str) -> Member:
        """Set a member's default record page."""
        endpoint = f"members/{user_id}/defaultRecordPage"
        d = self._request("PUT", endpoint, page=page)
        return Member(d, client=self)

    def get_member_groups(self, user_id: str = "me", **kwargs) -> list[Group]:
        """user_id can also be an e-mail address or simply 'me'"""
        endpoint = f"members/{user_id}/groups"
        d = self._request("GET", endpoint, **kwargs)
        return [Group(g, client=self) for g in d]

    def get_member_records(
        self,
        user_id: str = "me",
        filter: str | None = None,
        accessLevel: str | None = None,
        expand: str | None = None,
    ) -> list[Record]:
        """
        Get a member's records.

        Parameters
        ----------
        user_id : str
            The user ID, email address, or 'me'.
        filter : str, optional
            Can be 'open', 'closed' or 'all'. Default API behavior is 'open'.
        accessLevel : str, optional
            Can be 'owner', 'shared' or 'all'. Default API behavior is 'owner'.
        expand : str, optional
            Which nested resources to include. Can be 'owner' or 'none'.
        """
        endpoint = f"members/{user_id}/records"
        d = self._request(
            "GET",
            endpoint,
            filter=filter,
            accessLevel=accessLevel,
            expand=expand,
        )
        return [Record(r, client=self) for r in d]

    # ── Meters ────────────────────────────────────────────────

    def get_meter(self, meter_id: str) -> Meter:
        endpoint = f"meters/{meter_id}"
        d = self._request("GET", endpoint)
        return Meter(d, client=self)

    def get_meter_readings(
        self,
        meter_id: str,
        take: int = 1000,
        nextRowKey: str | None = None,
        **kwargs,
    ) -> dict:
        endpoint = f"meters/{meter_id}/readings"
        return self._request(
            "GET", endpoint, take=take, nextRowKey=nextRowKey, **kwargs
        )

    def get_meter_latest_reading(self, meter_id: str) -> dict:
        endpoint = f"meters/{meter_id}/readings/latest"
        return self._request("GET", endpoint)

    def create_meter_reading(
        self, meter_id: str, value: int | float, timestamp: str
    ) -> dict:
        endpoint = f"meters/{meter_id}/readings"
        return self._request("POST", endpoint, value=value, timestamp=timestamp)

    def _create_meter(self, **kwargs) -> Meter:
        endpoint = "meters"
        d = self._request("POST", endpoint, **kwargs)
        return Meter(d, client=self)

    def create_meter(
        self,
        record_id: str,
        display_name: str,
        metric: str,
        unit: str,
        reading_type: str,
        **kwargs,
    ) -> Meter:
        """
        Create a new meter.

        Parameters
        ----------
        record_id : str
            The record ID string (e.g. 'EA-14092736').
        display_name : str
            The name for the meter.
        metric : str
            The metric that is being measured.
        unit : str
            The unit in which the meter readings are expressed.
        reading_type : str
            Determines how readings should be interpreted.
        **kwargs
            Additional parameters: multiplier, excludeFromReports,
            stockCapacity, renewable, supplier, installationNumber,
            connectionNumber, brandName, modelName, peakPower,
            meterNumber, comments, hidden.
        """
        meter = self._create_meter(
            recordId=record_id,
            displayName=display_name,
            metric=metric,
            unit=unit,
            readingType=reading_type,
            **kwargs,
        )
        return meter

    def hide_meter(self, meter_id: str, hidden: bool = True) -> Meter:
        endpoint = f"meters/{meter_id}/hidden"
        d = self._request("POST", endpoint, hidden=hidden)
        return Meter(d, client=self)

    def close_meter(self, meter_id: str, closed: bool = True) -> dict:
        """Close or reopen a meter."""
        endpoint = f"meters/{meter_id}/closed"
        return self._request("PUT", endpoint, value=closed)

    def edit_meter(self, meter_id: str, **kwargs) -> Meter:
        endpoint = f"meters/{meter_id}"
        d = self._request("PUT", endpoint, **kwargs)
        return Meter(d, client=self)

    @staticmethod
    def _get_meter_data_kwargs(
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
                pd.date_range(
                    start=start, end=end, freq=freqs[interval], normalize=True
                )
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

    def get_meter_data(
        self,
        meter_id: str,
        start: str | pd.Timestamp | None = None,
        end: str | pd.Timestamp | None = None,
        interval: str = "P1D",
    ) -> list[dict]:
        calls = self._get_meter_data_kwargs(
            meter_id=meter_id, start=start, end=end, interval=interval
        )
        responses = [self._request(**call) for call in calls]
        return responses

    def get_meter_reading(self, meter_id: str, key: str) -> dict:
        endpoint = f"meters/{meter_id}/readings/{key}"
        return self._request("GET", endpoint)

    def edit_meter_reading(
        self, meter_id: str, key: str, new_value: int | float
    ) -> dict:
        endpoint = f"meters/{meter_id}/readings/{key}/value"
        return self._request("PUT", endpoint, newValue=new_value)

    def edit_meter_reading_status(
        self, meter_id: str, key: str, new_status: str
    ) -> dict:
        endpoint = f"meters/{meter_id}/readings/{key}/status"
        return self._request("PUT", endpoint, statuscode=new_status)

    def ignore_meter_reading(
        self, meter_id: str, key: str, ignore: bool = True
    ) -> dict:
        endpoint = f"meters/{meter_id}/readings/{key}/ignore"
        return self._request("PUT", endpoint, ignore=ignore)

    def delete_meter(self, meter_id: str) -> None:
        endpoint = f"meters/{meter_id}"
        self._request("DELETE", endpoint)

    def delete_meter_reading(self, meter_id: str, key: str) -> None:
        endpoint = f"meters/{meter_id}/readings/{key}"
        self._request("DELETE", endpoint)

    # ── Organizations ─────────────────────────────────────────

    def get_organization(self, org_id: str) -> Organization:
        """Get an organization. org_id can also be the organization slug."""
        endpoint = f"organizations/{org_id}"
        d = self._request("GET", endpoint)
        return Organization(d, client=self)

    def get_organization_groups(
        self, org_id: str, lang: str | None = None
    ) -> list[Group]:
        """List the groups of an organization."""
        endpoint = f"organizations/{org_id}/groups"
        d = self._request("GET", endpoint, lang=lang)
        return [Group(g, client=self) for g in d]

    # ── Records ───────────────────────────────────────────────

    def get_record(self, record_id: int, **kwargs) -> Record:
        endpoint = f"records/{record_id}"
        d = self._request("GET", endpoint, **kwargs)
        return Record(d, client=self)

    def get_record_meters(
        self, record_id: int, filter: dict = None, **kwargs
    ) -> list[Meter]:
        endpoint = f"records/{record_id}/meters"
        d = self._request("GET", endpoint, **kwargs)
        meters = [Meter(m, client=self) for m in d]
        if filter:
            for key in filter:
                meters = [meter for meter in meters if meter[key] == filter[key]]
        return meters

    def get_record_groups(self, record_id: int, **kwargs) -> list[Group]:
        endpoint = f"records/{record_id}/groups"
        d = self._request("GET", endpoint, **kwargs)
        return [Group(g, client=self) for g in d]

    def get_record_data(
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
        return self._request(
            "GET",
            endpoint,
            start=start,
            end=end,
            filter=filter,
            interval=interval,
            grouping=grouping,
            **kwargs,
        )

    def get_record_directives(self, record_id: str) -> list[dict]:
        """List all directives for a record."""
        endpoint = f"records/{record_id}/directives"
        return self._request("GET", endpoint)

    def get_record_directive_signals(
        self,
        record_id: str,
        directive_id: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict:
        """Get the latest signals for a directive."""
        endpoint = f"records/{record_id}/directives/{directive_id}"
        return self._request("GET", endpoint, limit=limit, offset=offset)

    def get_record_activity(
        self,
        record_id: str,
        take: int = 100,
        nextRowKey: str | None = None,
    ) -> dict:
        """Get a record's activity log entries."""
        endpoint = f"records/{record_id}/activity"
        return self._request("GET", endpoint, take=take, nextRowKey=nextRowKey)

    def get_record_timeline(
        self, record_id: str, from_date: str, to_date: str
    ) -> list[dict]:
        """
        List the timeline items of a record.

        Parameters
        ----------
        record_id : str
            The ID of the record.
        from_date : str
            Start date (YYYY-MM-DD).
        to_date : str
            End date (YYYY-MM-DD).
        """
        endpoint = f"records/{record_id}/timeline"
        # API parameter names are 'from' and 'to'
        return self._request("GET", endpoint, **{"from": from_date, "to": to_date})

    def create_timeline_item(
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
        """Create a new timeline item for a record."""
        endpoint = f"records/{record_id}/timeline"
        return self._request(
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

    def update_timeline_item(
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
        """Update a timeline item."""
        endpoint = f"records/{record_id}/timeline/{item_id}"
        return self._request(
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

    def delete_timeline_item(self, record_id: str, item_id: str) -> None:
        """Delete a timeline item."""
        endpoint = f"records/{record_id}/timeline/{item_id}"
        self._request("DELETE", endpoint)

    def get_record_limits(self, record_id: str) -> list[dict]:
        """List the limits for a record."""
        endpoint = f"records/{record_id}/limits"
        return self._request("GET", endpoint)

    def get_record_benchmark(
        self,
        record_id: str,
        name: str,
        year: int,
        month: int | None = None,
    ) -> dict:
        """Benchmark aggregated metrics for a record."""
        endpoint = f"records/{record_id}/benchmark/{name}"
        return self._request("GET", endpoint, year=year, month=month)

    def get_record_benchmark_filtered(
        self,
        record_id: str,
        name: str,
        filter: str,
        year: int,
        month: int | None = None,
    ) -> dict:
        """Benchmark aggregated metrics that match a given filter."""
        endpoint = f"records/{record_id}/benchmark/{name}/{filter}"
        return self._request("GET", endpoint, year=year, month=month)

    def _create_record(self, **kwargs) -> Record:
        endpoint = "records"
        d = self._request("POST", endpoint, **kwargs)
        return Record(d, client=self)

    def create_record(
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
        """
        Create a new record.

        Parameters
        ----------
        display_name : str
            The display name of the record. Required.
        record_type : str
            The type of record: 'household', 'business', or 'productionUnit'. Required.
        city : str
            The city of the building. Required.
        postal_code : str
            The postal code. Required.
        country : str
            Country code: 'bE', 'nL', 'fR', 'pT', 'iT'. Required.
        category : str
            Building category. Required.
        street_address : str, optional
        tags : list[str], optional
        dwelling_type : int, optional
        occupants : int, optional
        principal_residence : bool, optional
        heating_on : int, optional
        auxiliary_heating_on : int, optional
        hot_water_on : int, optional
        cooking_on : int, optional
        occupier_type : int, optional
        floor_surface : float, optional
        year_of_construction : int, optional
        year_of_renovation : int, optional
        energy_performance : float, optional
        energy_rating : float, optional
        energy_efficiency : int, optional
        installations : str, optional
        workspace_id : str, optional
        """
        record = self._create_record(
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

    def edit_record(self, record_id: int, **kwargs) -> Record:
        endpoint = f"records/{record_id}"
        d = self._request("PUT", endpoint, **kwargs)
        return Record(d, client=self)

    def delete_record(self, record_id: int) -> None:
        endpoint = f"records/{record_id}"
        self._request("DELETE", endpoint)

    def get_record_definitions(self, record_id: str) -> list[dict]:
        endpoint = f"records/{record_id}/definitions"
        return self._request("GET", endpoint)["data"]

    # ── Search ────────────────────────────────────────────────

    def search_groups(self, q: str = None, **kwargs) -> list[Group]:
        endpoint = "search/groups"
        d = self._request("GET", endpoint, q=q, **kwargs)
        return [Group(g, client=self) for g in d]

    def search_services(
        self, q: str = None, top: int = 100, skip: int = 0, **kwargs
    ) -> list[dict]:
        """Search for services."""
        endpoint = "search/services"
        return self._request("GET", endpoint, q=q, top=top, skip=skip, **kwargs)

    def search_cities(self, country: str, query: str, **kwargs) -> dict:
        endpoint = "search/cities"
        return self._request("GET", endpoint, country=country, query=query, **kwargs)

    # ── Transfers ─────────────────────────────────────────────

    def create_transfer(
        self, record_id: str, email: str, remarks: str | None = None
    ) -> dict:
        """Create a record transfer."""
        endpoint = "transfers"
        return self._request(
            "POST", endpoint, recordId=record_id, email=email, remarks=remarks
        )

    def cancel_transfer(self, transfer_id: str) -> None:
        """Cancel a record transfer."""
        endpoint = f"transfers/{transfer_id}"
        self._request("DELETE", endpoint)

    def accept_transfer(self, transfer_id: str) -> dict:
        """Accept a record transfer."""
        endpoint = f"transfers/{transfer_id}/accept"
        return self._request("PUT", endpoint)

    def decline_transfer(self, transfer_id: str) -> dict:
        """Decline a record transfer."""
        endpoint = f"transfers/{transfer_id}/decline"
        return self._request("PUT", endpoint)
