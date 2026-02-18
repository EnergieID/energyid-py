from ...models import Group


class SearchMixin:
    async def search_groups(self, q: str = None, **kwargs) -> list[Group]:
        d = await self._request("GET", "search/groups", q=q, **kwargs)
        return [Group(g, client=self) for g in d]

    async def search_services(
        self, q: str = None, top: int = 100, skip: int = 0, **kwargs
    ) -> list[dict]:
        return await self._request(
            "GET", "search/services", q=q, top=top, skip=skip, **kwargs
        )

    async def search_cities(self, country: str, query: str, **kwargs) -> dict:
        return await self._request(
            "GET", "search/cities", country=country, query=query, **kwargs
        )
