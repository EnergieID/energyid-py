import requests
from typing import Union, Optional

from .models import Group, Record, User, Meter

URL = "https://api.energyid.eu/api/v1"

class JSONClient:
    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"bearer {token}"})

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = f'{URL}/{endpoint}'
        if method == 'GET':
            r = self.session.get(url, params=kwargs)
        elif method == 'POST':
            r = self.session.post(url, data=kwargs)
        elif method == 'PUT':
            r = self.session.put(url, data=kwargs)
        elif method == 'DELETE':
            r = self.session.delete(url)
            r.raise_for_status()
            return {}
        else:
            raise ValueError(f'Unknown method: {method}')
        r.raise_for_status()
        j = r.json()
        return j

    def get_meter_catalog(self) -> dict:
        endpoint = 'catalogs/meters'
        return self._request('GET', endpoint)

    def get_dataset_catalog(self) -> dict:
        endpoint = 'catalogs/datasets'
        return self._request('GET', endpoint)

    def get_group(self, group_id: str, **kwargs) -> Group:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}'
        d = self._request('GET', endpoint, **kwargs)
        return Group(d, client=self)

    def get_group_languages(self, group_id: str) -> [str]:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/languages'
        return self._request('GET', endpoint)

    def get_group_records(self, group_id: str, top: int=200, skip: int=0) -> [Record]:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/records'
        d = self._request('GET', endpoint, top=top, skip=skip)
        return [Record(r, client=self) for r in d]

    def get_group_members(self, group_id: str, top: int=200, skip: int=0) -> [User]:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/members'
        d = self._request('GET', endpoint, top=top, skip=skip)
        return [User(u, client=self) for u in d]

    def get_records_for_group_member(self, group_id: str, user_id: str='me') -> [Record]:
        """
        group_id can also be the group slug
        user_id can also be an e-mail address or simply 'me'
        """
        endpoint = f'groups/{group_id}/members/{user_id}/records'
        d = self._request('GET', endpoint)
        return [Record(r, client=self) for r in d]

    def get_group_membership_details(self, group_id: str, record_id: str) -> dict:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/records/{record_id}'
        return self._request('GET', endpoint)

    def add_record_to_group(self, group_id: str, record_number: str, identification_key: Optional[str]=None) -> dict:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/records'
        return self._request('POST', endpoint, RecordNumber=record_number, IdentificationKey=identification_key)

    def change_reference_of_record_in_group(self, group_id: str, record_id: str, reference: Optional[str]=None) -> dict:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/records/{record_id}/reference'
        return self._request('PUT', endpoint, newReference=reference)

    def remove_record_from_group(self, group_id: str, record_id: str):
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/records/{record_id}'
        self._request('DELETE', endpoint)

    def get_member(self, user_id: str='me') -> dict:
        """user_id can also be an e-mail address or simply 'me'"""
        endpoint = f'members/{user_id}'
        d = self._request('GET', endpoint)
        return User(d, client=self)

    def get_member_groups(self, user_id: str='me', **kwargs) -> [Group]:
        """user_id can also be an e-mail address or simply 'me'"""
        endpoint = f'members/{user_id}/groups'
        d = self._request('GET', endpoint, **kwargs)
        return [Group(g, client=self) for g in d]

    def get_member_records(self, user_id: str='me') -> [Record]:
        """user_id can also be an e-mail address or simply 'me'"""
        endpoint = f'members/{user_id}/records'
        d = self._request('GET', endpoint)
        return [Record(r, client=self) for r in d]

    def get_meter(self, meter_id: str) -> dict:
        endpoint = f'meters/{meter_id}'
        d = self._request('GET', endpoint)
        return Meter(d, client=self)

    def get_meter_readings(self, meter_id: str, take: int=1000, skip: int=0, next_key: Optional[str]=None) -> dict:
        endpoint = f'meters/{meter_id}/readings'
        return self._request('GET', endpoint, take=take, skip=skip, nextRowKey=next_key)

    def get_meter_latest_reading(self, meter_id: str) -> dict:
        endpoint = f'meters/{meter_id}/readings/latest'
        return self._request('GET', endpoint)

    def create_meter_reading(self, meter_id: str, value: Union[int, float], timestamp: Optional[str]=None) -> dict:
        endpoint = f'meters/{meter_id}/readings'
        return self._request('POST', endpoint, value=value, timestamp=timestamp)

    def create_meter(self, record_number: str, display_name: str, metric: str, unit: str, reading_type: str,
                     multiplier: Union[int, float]=1, **kwargs):
        endpoint = f'meters'
        d = self._request('POST', endpoint, recordNumber=record_number, displayName=display_name, metric=metric,
                          unit=unit, readingType=reading_type, multiplier=multiplier, **kwargs)
        return Meter(d, client=self)

