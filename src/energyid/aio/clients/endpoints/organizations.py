from ...models import Group, Organization


class OrganizationsMixin:
    async def get_organization(self, org_id: str) -> Organization:
        endpoint = f"organizations/{org_id}"
        d = await self._request("GET", endpoint)
        return Organization(d, client=self)

    async def get_organization_groups(
        self, org_id: str, lang: str | None = None
    ) -> list[Group]:
        endpoint = f"organizations/{org_id}/groups"
        d = await self._request("GET", endpoint, lang=lang)
        return [Group(g, client=self) for g in d]
