from ...models import Group, Member, Record


class MembersMixin:
    async def get_member(self, user_id: str = "me") -> Member:
        endpoint = f"members/{user_id}"
        d = await self._request("GET", endpoint)
        return Member(d, client=self)

    async def update_member(
        self,
        user_id: str,
        full_name: str,
        initials: str,
        biography: str | None = None,
    ) -> Member:
        endpoint = f"members/{user_id}"
        d = await self._request(
            "PUT",
            endpoint,
            fullName=full_name,
            initials=initials,
            biography=biography,
        )
        return Member(d, client=self)

    async def get_member_limits(self, user_id: str = "me") -> list[dict]:
        endpoint = f"members/{user_id}/limits"
        return await self._request("GET", endpoint)

    async def set_member_language(self, user_id: str, lang: str) -> Member:
        endpoint = f"members/{user_id}/lang"
        d = await self._request("PUT", endpoint, lang=lang)
        return Member(d, client=self)

    async def set_member_default_record(self, user_id: str, record_id: str) -> Member:
        endpoint = f"members/{user_id}/defaultRecord"
        d = await self._request("PUT", endpoint, recordId=record_id)
        return Member(d, client=self)

    async def set_member_default_record_page(self, user_id: str, page: str) -> Member:
        endpoint = f"members/{user_id}/defaultRecordPage"
        d = await self._request("PUT", endpoint, page=page)
        return Member(d, client=self)

    async def get_member_groups(self, user_id: str = "me", **kwargs) -> list[Group]:
        endpoint = f"members/{user_id}/groups"
        d = await self._request("GET", endpoint, **kwargs)
        return [Group(g, client=self) for g in d]

    async def get_member_records(
        self,
        user_id: str = "me",
        filter: str | None = None,
        accessLevel: str | None = None,
        expand: str | None = None,
    ) -> list[Record]:
        endpoint = f"members/{user_id}/records"
        d = await self._request(
            "GET",
            endpoint,
            filter=filter,
            accessLevel=accessLevel,
            expand=expand,
        )
        return [Record(r, client=self) for r in d]
