from typing import Optional, Union, Iterator, List, TYPE_CHECKING
from json import JSONDecodeError
import pandas as pd

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


class Member(Model):
    def get_groups(self, filter='all') -> List['Group']:
        return self.client.get_member_groups(user_id=self.id, filter=filter)

    def get_records(self) -> List['Record']:
        return self.client.get_member_records(user_id=self.id)


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

    def get_data(self, **kwargs):
        return self.client.get_meter_data(meter_id=self.id, **kwargs)

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
    @property
    def id(self) -> Union[str, int]:
        try:
            return super(Record, self).id
        except KeyError:
            return self['recordId']

    @property
    def timezone(self) -> str:
        try:
            return self['timeZone']
        except KeyError:
            self.extend_info()
            return self['timeZone']

    @property
    def number(self) -> str:
        try:
            return self['recordNumber']
        except KeyError:
            self.extend_info()
            return self['recordNumber']

    def add_to_group(self, group_id: str, access_key: Optional[str]=None) -> None:
        """group_id can also be the group slug"""
        self.client.add_record_to_group(group_id=group_id, record_id=self.id, access_key=access_key)

    def change_reference_in_group(self, group_id: str, reference: Optional[str]=None) -> None:
        """group_id can also be the group slug"""
        self.client.change_reference_of_record_in_group(group_id=group_id, record_id=self.id, reference=reference)

    def remove_from_group(self, group_id: str) -> None:
        """group_id can also be the group slug"""
        self.client.remove_record_from_group(group_id=group_id, record_id=self.id)

    def get_meters(self, **kwargs) -> List[Meter]:
        return self.client.get_record_meters(record_id=self.id, **kwargs)

    def get_groups(self) -> List['Group']:
        return self.client.get_record_groups(record_id=self.id)

    def get_data(self, name: str, start: str = None, end: str = None,
                 interval: str = 'day', filter: str = None, **kwargs) -> dict:
        return self.client.get_record_data(
            record_id=self.id, name=name, start=start, end=end,
            interval=interval, filter=filter, **kwargs)

    def edit(self, **kwargs) -> None:
        self.client.edit_record(record_id=self.id, **kwargs)

    def delete(self) -> None:
        self.client.delete_record(record_id=self.id)

    def create_meter(self, display_name: str, metric: str, unit: str, reading_type: str, **kwargs) -> Meter:
        return self.client.create_meter(record_id=self.id, display_name=display_name, metric=metric, unit=unit,
                                        reading_type=reading_type, **kwargs)

    def extend_info(self):
        """You might get a record with limited info. Use this to extend the info"""
        record = self.client.get_record(record_id=self.id)
        self.update(record)


class Group(Model):
    def get_members(self, amount: Optional[int]=None, chunk_size=200) -> Iterator[Member]:
        """Use amount=None to get all members"""
        members = handle_skip_top_limit(self.client.get_group_members, group_id=self.id, amount=amount,
                                        chunk_size=chunk_size)
        return members

    def get_records(self, amount: Optional[int]=None, chunk_size=200) -> Iterator[Record]:
        """Use amount=None to get all records"""
        records = handle_skip_top_limit(self.client.get_group_records, group_id=self.id, amount=amount,
                                        chunk_size=chunk_size)
        return records

    def add_record(self, record_id: int, access_key: Optional[str]=None) -> None:
        self.client.add_record_to_group(group_id=self.id, record_id=record_id, access_key=access_key)

    def change_reference_of_record(self, record_id: int, reference: Optional[str]=None) -> None:
        self.client.change_reference_of_record_in_group(group_id=self.id, record_id=record_id, reference=reference)

    def remove_record(self, record_id: int) -> None:
        self.client.remove_record_from_group(group_id=self.id, record_id=record_id)

    def get_individual_data(self, name: str, start: str = None, end: str = None,
                 interval: str = 'day', filter: str = None, **kwargs):
        def _gen_data():
            for record in self.get_records(**kwargs):
                ts = record.get_data(name=name, start=start, end=end,
                                     interval=interval, filter=filter, **kwargs)
                ts.name = record.number
                yield ts
        data = _gen_data()
        data = (ts for ts in data if not ts.empty)
        df = pd.concat(data, axis=1)
        return df

    def get_records_dataframe(self, amount: Optional[int]=None) -> pd.DataFrame:
        records = self.get_records(amount=amount)
        record_list = []
        for record in records:
            record.extend_info()
            record_list.append(record)
        df = pd.DataFrame.from_dict(record_list)
        return df
