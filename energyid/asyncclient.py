import functools
from functools import wraps
import datetime as dt
from typing import Optional, Set, Dict, Union, List
from urllib.parse import quote

import aiohttp
import asyncio

import pandas as pd

from energyid import PandasClient
from energyid.client import BaseClient, Scope, JSONClient
from energyid.models import Member


def authenticated(func):
    """
    Decorator to check if access token has expired.
    If it has, use the refresh token to request a new access token
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        self = args[0]
        if self.token is None:
            async with self.auth_lock:
                if self.token is None:
                    if self._username is not None and self._password is not None:
                        await self.authenticate(username=self._username,
                                          password=self._password, scopes=self._scopes)
                    else:
                        raise PermissionError('You haven\'t authenticated yet and '
                                              'have not provided credentials!')
        if self._refresh_token is not None and \
           self._token_expiration_time <= dt.datetime.utcnow():
            async with self.auth_lock:
                if self._refresh_token is not None and \
                        self._token_expiration_time <= dt.datetime.utcnow():
                    await self._re_authenticate()
        return await func(*args, **kwargs)
    return wrapper


class AsyncBaseClient(BaseClient):
    def __init__(
            self,
            client_id: str,
            client_secret: str,
            username: str,
            password: str,
            scopes: Optional[Set[Scope]] = (Scope.RECORDS_READ,
                                            Scope.PROFILE_READ,
                                            Scope.GROUPS_READ),
            session: Optional[aiohttp.ClientSession] = None
    ):
        super(AsyncBaseClient, self).__init__(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            scopes=scopes
        )
        self._session = session
        self._auth_lock: Optional[asyncio.Lock] = None

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        await self.session.close()

    @property
    def auth_lock(self) -> asyncio.Lock:
        if self._auth_lock is None:
            return asyncio.Lock()
        else:
            return self._auth_lock

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def authenticate(self, username: str, password: str,
                     scopes: Set[Scope] = (Scope.RECORDS_READ, Scope.PROFILE_READ, Scope.GROUPS_READ)):
        await self._auth_request(
            data=self._auth_params(
                username=username,
                password=password,
                scopes=scopes
            )
        )

    async def _re_authenticate(self):
        await self._auth_request(data=self._re_auth_params())

    async def _auth_request(self, data: Dict):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data.update({'client_id': self._client_id, 'client_secret': self._client_secret})
        async with self.session.post(url=self.AUTH_URL, data=data,
                                      headers=headers) as r:
            r.raise_for_status()
            response = await r.json()
        self.token = response['access_token']
        self._refresh_token = response.get('refresh_token')
        self._set_token_expiration_time(expires_in=response['expires_in'])

    @authenticated
    @functools.lru_cache(maxsize=128, typed=False)
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        headers = {'Content-Type': 'application/json'}
        endpoint = quote(endpoint)
        url = f'{self.URL}/{endpoint}'
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        async with self.session.request(method=method, url=url,
                                         headers=headers, params=kwargs) as r:
            r.raise_for_status()
            if method == 'DELETE':
                return {}
            j = await r.json()
        return j


class AsyncJSONClient(AsyncBaseClient, JSONClient):
    async def get_member(self, user_id: str = 'me') -> Member:
        d = await self._request(**self._get_member_kwargs(user_id=user_id))
        return Member(d, client=self)

    async def get_meter_data(
            self,
            meter_id: str,
            start: Optional[Union[str, pd.Timestamp]] = None,
            end: Optional[Union[str, pd.Timestamp]] = None,
            interval: str = "P1D"
    ) -> List[Dict]:
        calls = self._get_meter_data_kwargs(
            meter_id=meter_id,
            start=start,
            end=end,
            interval=interval
        )
        requests = [self._request(**call) for call in calls]
        resp = await asyncio.gather(*requests)
        return resp


class AsyncPandasClient(AsyncJSONClient, PandasClient):
    async def get_meter_data(self, meter_id: str, **kwargs) -> pd.Series:
        d = await super(AsyncPandasClient, self).get_meter_data(
            meter_id=meter_id, **kwargs)
        ts = self._parse_meter_data_multiple(data=d, meter_id=meter_id)
        return ts
