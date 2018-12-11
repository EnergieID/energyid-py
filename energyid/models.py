from typing import Optional, Union, Iterator, List, TYPE_CHECKING
from json import JSONDecodeError

from .misc import handle_skip_top_limit
if TYPE_CHECKING:
    from .client import JSONClient


class Model(dict):
    def __init__(self, *args, client=None, **kwargs):
        super(Model, self).__init__(*args, **kwargs)
        self.client: 'JSONClient' = client

    @property
    def id(self) -> Union[str, int]:
        return self['id']


class User(Model):
    def get_records_in_group(self, group_id: str) -> List['Record']:
        """group_id can also be the group slug"""
        return self.client.get_records_for_group_member(group_id=group_id, user_id=self.id)

    def get_groups(self, filter='all') -> List['Group']:
        return self.client.get_member_groups(user_id=self.id, filter=filter)

    def get_records(self) -> List['Record']:
        return self.client.get_member_records(user_id=self.id)

    def search_records(self, q: str, **kwargs) -> List['Record']:
        return self.client.search_records(q=q, user_id=self.id, **kwargs)


class Meter(Model):
    def create_reading(self, timestamp: str, value: Union[int, float]) -> dict:
        return self.client.create_meter_reading(meter_id=self.id, timestamp=timestamp, value=value)

    def hide(self, hidden: bool=True) -> None:
        self.client.hide_meter(meter_id=self.id, hidden=hidden)
        self.update({'hidden': hidden})

    def edit(self, **kwargs) -> None:
        self.client.edit_meter(meter_id=self.id, **kwargs)

    def get_readings(self, **kwargs) -> dict:
        return self.client.get_meter_readings(meter_id=self.id, **kwargs)

    def get_reading(self, key: str) -> dict:
        return self.client.get_meter_reading(meter_id=self.id, key=key)

    def get_latest_reading(self) -> dict:
        try:
            return self.client.get_meter_latest_reading(meter_id=self.id)
        except JSONDecodeError:  # TODO: check if API returns empty object after next deploy
            return {}

    def edit_reading(self, key: str, new_value: Union[int, float]) -> None:
        self.client.edit_meter_reading(meter_id=self.id, key=key, new_value=new_value)

    def edit_reading_status(self, key: str, new_status: str) -> None:
        self.client.edit_meter_reading_status(meter_id=self.id, key=key, new_status=new_status)

    def ignore_meter_reading(self, key: str, ignore: bool=True) -> None:
        self.client.ignore_meter_reading(meter_id=self.id, key=key, ignore=ignore)

    def delete(self) -> None:
        self.client.delete_meter(meter_id=self.id)

    def delete_reading(self, key: str) -> None:
        self.client.delete_meter_reading(meter_id=self.id, key=key)


class Record(Model):
    def get_group_membership_details(self, group_id: str) -> dict:
        """group_id can also be the group slug"""
        return self.client.get_group_membership_details(group_id=group_id, record_id=self.id)

    def add_to_group(self, group_id: str, access_key: Optional[str]=None) -> None:
        """group_id can also be the group slug"""
        self.client.add_record_to_group(group_id=group_id, record_id=self.id, access_key=access_key)

    def change_reference_in_group(self, group_id: str, reference: Optional[str]=None) -> None:
        """group_id can also be the group slug"""
        self.client.change_reference_of_record_in_group(group_id=group_id, record_id=self.id, reference=reference)

    def remove_from_group(self, group_id: str) -> None:
        """group_id can also be the group slug"""
        self.client.remove_record_from_group(group_id=group_id, record_id=self.id)

    def get_properties(self) -> dict:
        return self.client.get_record_properties(record_id=self.id)

    def get_meters(self) -> List[Meter]:
        return self.client.get_record_meters(record_id=self.id)

    def get_groups(self) -> List['Group']:
        return self.client.get_record_groups(record_id=self.id)

    def get_data(self, theme: str, dataset: str, **kwargs) -> dict:
        return self.client.get_record_data(record_id=self.id, theme=theme, dataset=dataset, **kwargs)

    def get_waste_data(self, **kwargs) -> dict:
        return self.client.get_record_waste_data(record_id=self.id, **kwargs)

    def edit(self, **kwargs) -> None:
        self.client.edit_record(record_id=self.id, **kwargs)

    def delete(self) -> None:
        self.client.delete_record(record_id=self.id)

    def create_meter(self, display_name: str, metric: str, unit: str, reading_type: str, **kwargs) -> Meter:
        return self.client.create_meter(record_id=self.id, display_name=display_name, metric=metric, unit=unit,
                                        reading_type=reading_type, **kwargs)


class Group(Model):
    def get_languages(self) -> List[str]:
        return self.client.get_group_languages(group_id=self.id)

    def get_members(self, amount: Optional[int]=None, chunk_size=200) -> Iterator[User]:
        """Use amount=None to get all members"""
        members = handle_skip_top_limit(self.client.get_group_members, group_id=self.id, amount=amount,
                                        chunk_size=chunk_size)
        return members

    def get_records(self, amount: Optional[int]=None, chunk_size=200) -> Iterator[Record]:
        """Use amount=None to get all records"""
        records = handle_skip_top_limit(self.client.get_group_records, group_id=self.id, amount=amount,
                                        chunk_size=chunk_size)
        return records

    def get_records_for_member(self, user_id: str='me') -> List[Record]:
        """user_id can also be an e-mail address or simply 'me'"""
        return self.client.get_records_for_group_member(group_id=self.id, user_id=user_id)

    def add_record(self, record_id: int, access_key: Optional[str]=None) -> None:
        self.client.add_record_to_group(group_id=self.id, record_id=record_id, access_key=access_key)

    def change_reference_of_record(self, record_id: int, reference: Optional[str]=None) -> None:
        self.client.change_reference_of_record_in_group(group_id=self.id, record_id=record_id, reference=reference)

    def remove_record(self, record_id: int) -> None:
        self.client.remove_record_from_group(group_id=self.id, record_id=record_id)
