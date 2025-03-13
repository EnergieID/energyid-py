from typing import TYPE_CHECKING
import energyid
import energyid.models

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