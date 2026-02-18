from ...models import Group, Member, Meter, Record


class GroupsMixin:
    async def get_group(self, group_id: str, **kwargs) -> Group:
        endpoint = f"groups/{group_id}"
        d = await self._request("GET", endpoint, **kwargs)
        return Group(d, client=self)

    async def get_group_records(
        self, group_id: str, take: int = 200, skip: int = 0, **kwargs
    ) -> list[Record]:
        endpoint = f"groups/{group_id}/records"
        d = await self._request("GET", endpoint, take=take, skip=skip, **kwargs)
        return [Record(r, client=self) for r in d]

    async def get_group_members(
        self, group_id: str, take: int = 200, skip: int = 0
    ) -> list[Member]:
        endpoint = f"groups/{group_id}/members"
        d = await self._request("GET", endpoint, take=take, skip=skip)
        return [Member(u, client=self) for u in d]

    async def get_group_meters(
        self, group_id: str, take: int = 200, skip: int = 0, **kwargs
    ) -> list[Meter]:
        endpoint = f"groups/{group_id}/meters"
        d = await self._request("GET", endpoint, take=take, skip=skip, **kwargs)
        return [Meter(m, client=self) for m in d]

    async def get_group_my_records(self, group_id: str, **kwargs) -> list[Record]:
        endpoint = f"groups/{group_id}/records/mine"
        d = await self._request("GET", endpoint, **kwargs)
        return [Record(r, client=self) for r in d]

    async def get_group_admins(self, group_id: str) -> list[dict]:
        endpoint = f"groups/{group_id}/admins"
        return await self._request("GET", endpoint)

    async def add_record_to_group(
        self, group_id: str, record_id: int, access_key: str | None = None
    ) -> dict:
        endpoint = f"groups/{group_id}/records"
        return await self._request(
            "POST", endpoint, recordId=record_id, accessKey=access_key
        )

    async def change_reference_of_record_in_group(
        self, group_id: str, record_id: int, reference: str | None = None
    ) -> dict:
        endpoint = f"groups/{group_id}/records/{record_id}/reference"
        return await self._request("PUT", endpoint, reference=reference)

    async def remove_record_from_group(self, group_id: str, record_id: int) -> None:
        endpoint = f"groups/{group_id}/records/{record_id}"
        await self._request("DELETE", endpoint)
