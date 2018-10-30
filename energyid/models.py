from typing import Optional

class Model(dict):
    def __init__(self, *args, client=None, **kwargs):
        super(Model, self).__init__(*args, **kwargs)
        self.client = client

class Meter(Model):
    pass

class Record(Model):
    def get_group_membership_details(self, group_id: str) -> dict:
        """group_id can also be the group slug"""
        return self.client.get_group_membership_details(group_id=group_id, record_id=self['id'])

    def add_to_group(self, group_id: str, identification_key: Optional[str]=None) -> dict:
        """group_id can also be the group slug"""
        return self.client.add_record_to_group(group_id=group_id, record_number=self['recordNumber'],
                                               identification_key=identification_key)

    def change_reference_in_group(self, group_id: str, reference: Optional[str]=None) -> dict:
        return self.client.change_reference_of_record_in_group(group_id=group_id, record_id=self['id'],
                                                               reference=reference)

    def remove_from_group(self, group_id: str):
        self.client.remove_record_from_group(group_id=group_id, record_id=self['id'])


class User(Model):
    def get_records_in_group(self, group_id: str) -> [Record]:
        """group_id can also be the group slug"""
        return self.client.get_records_for_group_member(group_id=group_id, user_id=self['id'])

    def get_groups(self, **kwargs):
        return self.client.get_member_groups(user_id=self['id'], **kwargs)

    def get_records(self) -> [Record]:
        return self.client.get_member_records(user_id=self['id'])


class Group(Model):
    def get_languages(self) -> [str]:
        return self.client.get_group_languages(group_id=self['id'])

    def get_members(self, **kwargs) -> [User]:
        return self.client.get_group_members(group_id=self['id'], **kwargs)

    def get_records_for_member(self, user_id: str) -> [Record]:
        """user_id can also be an e-mail address or simply 'me'"""
        return self.client.get_records_for_group_member(group_id=self['id'], user_id=user_id)

    def add_record(self, record_number: str, identification_key: Optional[str]=None) -> dict:
        return self.client.add_record_to_group(group_id=self['id'], record_number=record_number,
                                               identification_key=identification_key)

    def change_reference_of_record(self, record_id: str, reference: Optional[str]=None) -> dict:
        return self.client.change_reference_of_record_in_group(group_id=self['id'], record_id=record_id,
                                                               reference=reference)

    def remove_record(self, record_id: str):
        self.client.remove_record_from_group(group_id=self['id'], record_id=record_id)