import requests
from typing import Union, Optional, List

from .models import Group, Record, User, Meter

URL = "https://api.energyid.eu/api/v1"

class JSONClient:
    def __init__(self, token: str):
        self._token = token
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"bearer {token}"})

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, value):
        self._token = value
        self.session.headers.update({"Authorization": f"bearer {value}"})

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

    def get_dataset_catalog(self) -> List[str]:
        endpoint = 'catalogs/datasets'
        d = self._request('GET', endpoint)
        return list(d)

    def get_group(self, group_id: str, **kwargs) -> Group:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}'
        d = self._request('GET', endpoint, **kwargs)
        return Group(d, client=self)

    def get_group_languages(self, group_id: str) -> List[str]:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/languages'
        d = self._request('GET', endpoint)
        return list(d)

    def get_group_records(self, group_id: str, top: int=200, skip: int=0) -> List[Record]:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/records'
        d = self._request('GET', endpoint, top=top, skip=skip)
        # TODO: check if this returns a record or only scopes
        return [Record(r, client=self) for r in d]

    def get_group_members(self, group_id: str, top: int=200, skip: int=0) -> List[User]:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/members'
        d = self._request('GET', endpoint, top=top, skip=skip)
        return [User(u, client=self) for u in d]

    def get_records_for_group_member(self, group_id: str, user_id: str='me') -> List[Record]:
        """
        group_id can also be the group slug
        user_id can also be an e-mail address or simply 'me'
        """
        endpoint = f'groups/{group_id}/members/{user_id}/records'
        d = self._request('GET', endpoint)
        return [Record(r, client=self) for r in d]

    def get_group_membership_details(self, group_id: str, record_id: int) -> dict:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/records/{record_id}'
        return self._request('GET', endpoint)

    def add_record_to_group(self, group_id: str, record_id: int, access_key: Optional[str]=None) -> dict:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/records'
        return self._request('POST', endpoint, recordId=record_id, accessKey=access_key)

    def change_reference_of_record_in_group(self, group_id: str, record_id: int, reference: Optional[str]=None) -> dict:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/records/{record_id}/reference'
        return self._request('PUT', endpoint, newReference=reference)

    def remove_record_from_group(self, group_id: str, record_id: int) -> None:
        """group_id can also be the group slug"""
        endpoint = f'groups/{group_id}/records/{record_id}'
        self._request('DELETE', endpoint)

    # TODO: change to User after next deploy
    def get_member(self, user_id: str='me') -> User:
        """user_id can also be an e-mail address or simply 'me'"""
        endpoint = f'members/{user_id}'
        d = self._request('GET', endpoint)
        return User(d, client=self)

    # TODO: change to User after next deploy
    def get_member_groups(self, user_id: str='me', **kwargs) -> List[Group]:
        """user_id can also be an e-mail address or simply 'me'"""
        endpoint = f'members/{user_id}/groups'
        d = self._request('GET', endpoint, **kwargs)
        return [Group(g, client=self) for g in d]

    # TODO: change to User after next deploy
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

    def create_meter(self, record_id: int, display_name: str, metric: str, unit: str, reading_type: str,
                     **kwargs) -> Meter:
        endpoint = 'meters'
        # TODO: change recordNumber to recordid after next deploy
        d = self._request('POST', endpoint, recordNumber=f'EA-{record_id}', displayName=display_name, metric=metric,
                          unit=unit, readingType=reading_type, **kwargs)
        return Meter(d, client=self)

    def hide_meter(self, meter_id: str, hidden: bool=True) -> Meter:
        endpoint = f'meters/{meter_id}/hidden'
        d = self._request('POST', endpoint, hidden=hidden)
        return Meter(d, client=self)

    def edit_meter(self, meter_id: str, **kwargs) -> Meter:
        endpoint = f'meters/{meter_id}'
        d = self._request('PUT', endpoint, **kwargs)
        return Meter(d, client=self)

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

    def get_record_properties(self, record_id: int) -> dict:
        endpoint = f'records/{record_id}/properties'
        return self._request('GET', endpoint)

    def get_record_meters(self, record_id: int) -> List[Meter]:
        endpoint = f'records/{record_id}/meters'
        d = self._request('GET', endpoint)
        return [Meter(m, client=self) for m in d]

    def get_record_groups(self, record_id: int) -> List[Group]:
        endpoint = f'records/{record_id}/groups'
        d = self._request('GET', endpoint)
        return [Group(g, client=self) for g in d]

    def get_record_data(self, record_id: int, theme: str, dataset: str, **kwargs) -> dict:
        endpoint = f'records/{record_id}/data/{theme}/{dataset}'
        return self._request('GET', endpoint, **kwargs)

    def get_record_waste_data(self, record_id: int, **kwargs) -> dict:
        endpoint = f'records/{record_id}/data/waste'
        return self._request('GET', endpoint, **kwargs)

    def create_record(self, name: str, city: str, postalcode: str, country: str, record_type: str, category: str,
                      heating_on: str, auxiliary_heating_on: str, hot_water_on: str, cooking_on: str,
                      **kwargs) -> Record:
        endpoint = 'records'
        d = self._request('POST', endpoint, name=name, city=city, postalcode=postalcode, country=country,
                          recordtype=record_type, category=category, heatingon=heating_on,
                          auxiliaryheatingon=auxiliary_heating_on, hotwateron=hot_water_on, cookingon=cooking_on,
                          **kwargs)
        return Record(d, client=self)

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

    def search_records(self, q: str, user_id: str='me', **kwargs) -> List[Record]:
        endpoint = 'search/records'
        d = self._request('GET', endpoint, q=q, user=user_id, **kwargs)
        return [Record(r, client=self) for r in d]
