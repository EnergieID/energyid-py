import functools
import itertools
from enum import Enum
from functools import wraps

import pandas as pd
import requests
from urllib.parse import quote
from typing import Union, Optional, List, Dict, Set
import datetime as dt

from .models import Group, Record, Member, Meter


class Scope(Enum):
    RECORDS_WRITE = 'records:write'
    RECORDS_READ = 'records:read'
    PROFILE_WRITE = 'profile:write'
    PROFILE_READ = 'profile:read'
    GROUPS_WRITE = 'groups:write'
    GROUPS_READ= 'groups:read'


def authenticated(func):
    """
    Decorator to check if access token has expired.
    If it has, use the refresh token to request a new access token
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        if self.token is None:
            if self._username is not None and self._password is not None:
                self.authenticate(username=self._username,
                                  password=self._password, scopes=self._scopes)
            else:
                raise PermissionError('You haven\'t authenticated yet and '
                                      'have not provided credentials!')
        if self._refresh_token is not None and \
           self._token_expiration_time <= dt.datetime.utcnow():
            self._re_authenticate()
        return func(*args, **kwargs)
    return wrapper


class BaseClient:
    URL = "https://api.energyid.eu/api/v1"
    AUTH_URL = 'https://identity.energyid.eu/connect/token'

    def __init__(
            self,
            client_id: str,
            client_secret: str,
            username: Optional[str] = None,
            password: Optional[str] = None,
            scopes: Optional[Set[Scope]] = (Scope.RECORDS_READ,
                                            Scope.PROFILE_READ, Scope.GROUPS_READ),
            session: Optional[requests.Session] = None
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

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def _auth_params(
            self,
            username: str,
            password: str,
            scopes: Set[Scope]
    ) -> Dict:
        return {
            'grant_type': 'password',
            'username': username,
            'password': password,
            'scope': ' '.join(scope.value for scope in scopes) + ' offline_access'
        }

    def authenticate(self, username: str, password: str,
                     scopes: Set[Scope] = (Scope.RECORDS_READ, Scope.PROFILE_READ, Scope.GROUPS_READ)):
        self._auth_request(
            data=self._auth_params(
                username=username,
                password=password,
                scopes=scopes
            )
        )

    def _re_auth_params(self) -> Dict:
        return {'grant_type': 'refresh_token', 'refresh_token': self._refresh_token}

    def _re_authenticate(self):
        self._auth_request(data=self._re_auth_params())

    def _auth_request(self, data: Dict):
        self.session.headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data.update({'client_id': self._client_id, 'client_secret': self._client_secret})
        r = self.session.post(url=self.AUTH_URL, data=data)
        r.raise_for_status()
        response = r.json()
        self.token = response['access_token']
        self._refresh_token = response.get('refresh_token')
        self._set_token_expiration_time(expires_in=response['expires_in'])

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, value):
        self._token = value
        self.session.headers.update({"Authorization": f"bearer {value}"})

    def _set_token_expiration_time(self, expires_in):
        self._token_expiration_time = dt.datetime.utcnow() + \
                                      dt.timedelta(0, expires_in)  # timedelta(days, seconds)

    @authenticated
    @functools.lru_cache(maxsize=128, typed=False)
    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        self.session.headers.update({'Content-Type': 'application/json'})
        endpoint = quote(endpoint)
        url = f'{self.URL}/{endpoint}'
        if method == 'GET':
            r = self._session.get(url, params=kwargs)
        elif method == 'POST':
            r = self._session.post(url, params=kwargs)
        elif method == 'PUT':
            r = self._session.put(url, params=kwargs)
        elif method == 'DELETE':
            r = self._session.delete(url)
            r.raise_for_status()
            return {}
        else:
            raise ValueError(f'Unknown method: {method}')
        r.raise_for_status()
        j = r.json()
        return j


class JSONClient(BaseClient):
    def get_meter_catalog(self) -> dict:
        endpoint = 'catalogs/meters'
        return self._request('GET', endpoint)

    def get_group(self, group_id: str, **kwargs) -> Group:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}'
        d = self._request('GET', endpoint, **kwargs)
        return Group(d, client=self)

    def get_group_records(self, group_id: str, top: int=200, skip: int=0) -> List[Record]:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/records'
        d = self._request('GET', endpoint, top=top, skip=skip)
        # TODO: check if this returns a record or only scopes
        return [Record(r, client=self) for r in d]

    def get_group_members(self, group_id: str, top: int=200, skip: int=0) -> List[Member]:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/members'
        d = self._request('GET', endpoint, top=top, skip=skip)
        return [Member(u, client=self) for u in d]

    def add_record_to_group(self, group_id: str, record_id: int, access_key: Optional[str] = None) -> dict:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/records'
        return self._request('POST', endpoint, recordId=record_id, accessKey=access_key)

    def change_reference_of_record_in_group(self, group_id: str, record_id: int, reference: Optional[str] = None) -> dict:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/records/{record_id}/reference'
        return self._request('PUT', endpoint, reference=reference)

    def remove_record_from_group(self, group_id: str, record_id: int) -> None:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/records/{record_id}'
        self._request('DELETE', endpoint)

    @staticmethod
    def _get_member_kwargs(user_id: str = 'me') -> Dict:
        return dict(
            method='GET',
            endpoint=f'members/{user_id}'
        )

    def get_member(self, user_id: str = 'me') -> Member:
        """user_id can also be an e-mail address or simply 'me'"""
        d = self._request(**self._get_member_kwargs(user_id=user_id))
        return Member(d, client=self)

    def get_member_groups(self, user_id: str='me', **kwargs) -> List[Group]:
        """user_id can also be an e-mail address or simply 'me'"""
        endpoint = f'members/{user_id}/groups'
        d = self._request('GET', endpoint, **kwargs)
        return [Group(g, client=self) for g in d]

    def get_member_records(self, user_id: str='me') -> List[Record]:
        """user_id can also be an e-mail address or simply 'me'"""
        endpoint = f'members/{user_id}/records'
        d = self._request('GET', endpoint)
        return [Record(r, client=self) for r in d]

    def get_meter(self, meter_id: str) -> Meter:
        endpoint = f'meters/{meter_id}'
        d = self._request('GET', endpoint)
        return Meter(d, client=self)

    def get_meter_readings(self, meter_id: str, take: int=1000, skip: int=0, nextrowkey: Optional[str]=None) -> dict:
        endpoint = f'meters/{meter_id}/readings'
        return self._request('GET', endpoint, take=take, skip=skip, nextrowkey=nextrowkey)

    def get_meter_latest_reading(self, meter_id: str) -> dict:
        endpoint = f'meters/{meter_id}/readings/latest'
        return self._request('GET', endpoint)

    def create_meter_reading(self, meter_id: str, value: Union[int, float], timestamp: str) -> dict:
        endpoint = f'meters/{meter_id}/readings'
        return self._request('POST', endpoint, value=value, timestamp=timestamp)

    def _create_meter(self, **kwargs) -> Meter:
        endpoint = 'meters'
        d = self._request('POST', endpoint, **kwargs)
        return Meter(d, client=self)

    def create_meter(
            self, record_id: int, display_name: str, metric: str, unit: str,
            reading_type: str, **kwargs) -> Meter:
        meter = self._create_meter(
            recordId=f'EA-{record_id}', displayName=display_name,
            metric=metric, unit=unit, readingType=reading_type, **kwargs)
        return meter

    def hide_meter(self, meter_id: str, hidden: bool=True) -> Meter:
        endpoint = f'meters/{meter_id}/hidden'
        d = self._request('POST', endpoint, hidden=hidden)
        return Meter(d, client=self)

    def edit_meter(self, meter_id: str, **kwargs) -> Meter:
        endpoint = f'meters/{meter_id}'
        d = self._request('PUT', endpoint, **kwargs)
        return Meter(d, client=self)

    @staticmethod
    def _get_meter_data_kwargs(
            meter_id: str,
            start: Optional[Union[str, pd.Timestamp]] = None,
            end: Optional[Union[str, pd.Timestamp]] = None,
            interval: str = "P1D"
    ) -> List[Dict]:
        base = dict(
            method="GET",
            endpoint=f'meters/{meter_id}/data'
        )
        calls = []
        if start is not None and end is not None:
            start = pd.to_datetime(start)
            end = pd.to_datetime(end)

            freqs = {
                "PT5M": '2D',
                "PT15M": '7D',
                "PT1H": '31D',
                "P1D": '731D',
                "P7D": "3653D",
                "P1M": "3653D",
                "P1Y": "3653D"
            }
            dates = list(pd.date_range(start=start, end=end, freq=freqs[interval],
                                       normalize=True))
            dates.append(end)
            for _start, _end in itertools.pairwise(dates):
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
        responses = [self._request(**call) for call in calls]
        return responses

    def get_meter_reading(self, meter_id: str, key: str) -> dict:
        endpoint = f'meters/{meter_id}/readings/{key}'
        return self._request('GET', endpoint)

    def edit_meter_reading(self, meter_id: str, key: str, new_value: Union[int, float]) -> dict:
        endpoint = f'meters/{meter_id}/readings/{key}/value'
        return self._request('PUT', endpoint, newvalue=new_value)

    def edit_meter_reading_status(self, meter_id: str, key:str, new_status: str) -> dict:
        endpoint = f'meters/{meter_id}/readings/{key}/status'
        return self._request('PUT', endpoint, statuscode=new_status)

    def ignore_meter_reading(self, meter_id: str, key: str, ignore: bool=True) -> dict:
        endpoint = f'meters/{meter_id}/readings/{key}/ignore'
        return self._request('PUT', endpoint, ignore=ignore)

    def delete_meter(self, meter_id: str) -> None:
        endpoint = f'meters/{meter_id}'
        self._request('DELETE', endpoint)

    def delete_meter_reading(self, meter_id: str, key: str) -> None:
        endpoint = f'meters/{meter_id}/readings/{key}'
        self._request('DELETE', endpoint)

    def get_record(self, record_id: int) -> Record:
        endpoint = f'records/{record_id}'
        d = self._request('GET', endpoint)
        return Record(d, client=self)

    def get_record_meters(self, record_id: int, filter: Dict = None) -> List[Meter]:
        endpoint = f'records/{record_id}/meters'
        d = self._request('GET', endpoint)
        meters = [Meter(m, client=self) for m in d]
        if filter:
            for key in filter:
                meters = [meter for meter in meters if meter[key] == filter[key]]
        return meters

    def get_record_groups(self, record_id: int) -> List[Group]:
        endpoint = f'records/{record_id}/groups'
        d = self._request('GET', endpoint)
        return [Group(g, client=self) for g in d]

    def get_record_data(self, record_id: int, name: str, start: str, end: str,
                        interval: str = 'day', filter: str = None, **kwargs) -> dict:
        endpoint = f'records/{record_id}/data/{name}'
        return self._request('GET', endpoint, start=start, end=end,
                             filter=filter, interval=interval, **kwargs)

    def _create_record(self, **kwargs) -> Record:
        endpoint = 'records'
        d = self._request('POST', endpoint, **kwargs)
        return Record(d, client=self)

    def create_record(
            self, display_name: str, city: str, postalcode: str, country: str,
            record_type: str, category: str, heating_on: str,
            auxiliary_heating_on: str, hot_water_on: str, cooking_on: str,
            **kwargs) -> Record:
        record = self._create_record(
            displayname=display_name, city=city, postalcode=postalcode,
            country=country, recordtype=record_type, category=category,
            heatingon=heating_on, uxiliaryheatingon=auxiliary_heating_on,
            hotwateron=hot_water_on, cookingon=cooking_on, **kwargs)
        return record

    def edit_record(self, record_id: int, **kwargs) -> Record:
        endpoint = f'records/{record_id}'
        d = self._request('PUT', endpoint, **kwargs)
        return Record(d, client=self)

    def delete_record(self, record_id: int) -> None:
        endpoint = f'records/{record_id}'
        self._request('DELETE', endpoint)

    def search_groups(self, q: str, **kwargs) -> List[Group]:
        endpoint = 'search/groups'
        d = self._request('GET', endpoint, q=q, **kwargs)
        return [Group(g, client=self) for g in d]

    def get_record_definitions(self, record_id: str) -> List[Dict]:
        endpoint = f'records/{record_id}/definitions'
        return self._request('GET', endpoint)['data']

    def search_cities(self, country: str, query: str, **kwargs) -> Dict:
        endpoint = f'search/cities'
        return self._request('GET', endpoint, country=country, query=query,
                         **kwargs)


class SimpleJSONClient(JSONClient):
    """Simplified Client, for if you only have a token"""
    def __init__(self, token: str):
        # noinspection PyTypeChecker
        super(SimpleJSONClient, self).__init__(client_id=None, client_secret=None)
        self.token = token
