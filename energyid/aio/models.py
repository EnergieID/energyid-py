from typing import TYPE_CHECKING
import energyid
import energyid.models
from .misc import handle_skip_take_limit

if TYPE_CHECKING:
    from .client import JSONClient

class Model(energyid.models.Model):
    def __init__(self, *args, client=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.client: "JSONClient" = client

class Member(Model, energyid.models.Member):
    async def get_records(self):
        return await self.client.get_member_records(user_id=self.id)

class Record(Model, energyid.models.Record):
    pass

class Group(Model, energyid.models.Group):
    def get_records(self, amount=None, chunk_size=200, **kwargs):
        return handle_skip_take_limit(
            self.client.get_group_records,
            group_id=self.id,
            amount=amount,
            chunk_size=chunk_size,
            **kwargs
        )