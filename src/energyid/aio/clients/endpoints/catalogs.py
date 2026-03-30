class CatalogsMixin:
    async def get_meter_catalog(self) -> dict:
        return await self._request("GET", "catalogs/meters")
