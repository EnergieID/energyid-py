import asyncio
import datetime as dt
from functools import wraps
from urllib.parse import quote

import aiohttp

from energyid.scope import Scope

from .rate_limit import AsyncRequestLimiter


def authenticated(func):
    """
    Decorator to check if access token has expired.
    If it has, use the refresh token to request a new access token.
    Skipped entirely for API Key and Device Token auth.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        self = args[0]
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
                            "You haven't authenticated yet and have not provided credentials!"
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
        max_concurrency: int | None = 10,
        max_requests_per_window: int | None = 20,
        rate_limit_window_seconds: float = 1.0,
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

        self._request_limiter = AsyncRequestLimiter(
            max_concurrency=max_concurrency,
            max_requests_per_window=max_requests_per_window,
            rate_limit_window_seconds=rate_limit_window_seconds,
        )

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

        await self._request_limiter.acquire()
        try:
            async with self.session.request(
                method=method, url=url, headers=headers, params=kwargs
            ) as r:
                if r.status in (401, 403):
                    error_detail = await self._extract_error_detail(r)
                    suffix = f" Detail: {error_detail}" if error_detail else ""
                    raise aiohttp.ClientResponseError(
                        request_info=r.request_info,
                        history=r.history,
                        status=r.status,
                        message=(
                            f"{r.reason}. Authorization failed for this endpoint. "
                            "The token may be missing required permissions or expired."
                            f"{suffix}"
                        ),
                        headers=r.headers,
                    )
                r.raise_for_status()
                if method == "DELETE" or r.status == 204:
                    return {}
                payload = await r.json(content_type=None)
                return {} if payload is None else payload
        finally:
            self._request_limiter.release()

    @staticmethod
    async def _extract_error_detail(response: aiohttp.ClientResponse) -> str | None:
        try:
            payload = await response.json(content_type=None)
            if isinstance(payload, dict):
                for key in ("message", "error_description", "error", "detail"):
                    value = payload.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
            return None
        except Exception:
            try:
                text = await response.text()
                text = text.strip()
                return text or None
            except Exception:
                return None
