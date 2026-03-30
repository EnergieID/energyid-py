from ...models import Group, Meter, Record


class RecordsMixin:
    async def get_record(self, record_id: int, **kwargs) -> Record:
        endpoint = f"records/{record_id}"
        d = await self._request("GET", endpoint, **kwargs)
        return Record(d, client=self)

    async def get_record_meters(
        self, record_id: int, filter: dict = None, **kwargs
    ) -> list[Meter]:
        endpoint = f"records/{record_id}/meters"
        d = await self._request("GET", endpoint, **kwargs)
        meters = [Meter(m, client=self) for m in d]
        if filter:
            for key in filter:
                meters = [meter for meter in meters if meter[key] == filter[key]]
        return meters

    async def get_record_groups(self, record_id: int, **kwargs) -> list[Group]:
        endpoint = f"records/{record_id}/groups"
        d = await self._request("GET", endpoint, **kwargs)
        return [Group(g, client=self) for g in d]

    async def get_record_data(
        self,
        record_id: int,
        name: str,
        start: str,
        end: str,
        interval: str = "day",
        filter: str = None,
        grouping: str = None,
        **kwargs,
    ) -> dict:
        endpoint = f"records/{record_id}/data/{name}"
        return await self._request(
            "GET",
            endpoint,
            start=start,
            end=end,
            filter=filter,
            interval=interval,
            grouping=grouping,
            **kwargs,
        )

    async def get_record_directives(self, record_id: str) -> list[dict]:
        endpoint = f"records/{record_id}/directives"
        return await self._request("GET", endpoint)

    async def get_record_directive_signals(
        self,
        record_id: str,
        directive_id: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict:
        endpoint = f"records/{record_id}/directives/{directive_id}"
        return await self._request("GET", endpoint, limit=limit, offset=offset)

    async def get_record_activity(
        self,
        record_id: str,
        take: int = 100,
        nextRowKey: str | None = None,
    ) -> dict:
        endpoint = f"records/{record_id}/activity"
        return await self._request("GET", endpoint, take=take, nextRowKey=nextRowKey)

    async def get_record_timeline(
        self, record_id: str, from_date: str, to_date: str
    ) -> list[dict]:
        endpoint = f"records/{record_id}/timeline"
        return await self._request(
            "GET", endpoint, **{"from": from_date, "to": to_date}
        )

    async def create_timeline_item(
        self,
        record_id: str,
        display_name: str,
        start: str,
        description: str | None = None,
        type: str | None = None,
        private: bool | None = None,
        categories: str | None = None,
        customCategory: str | None = None,
        metadata: str | None = None,
        end: str | None = None,
        projectId: str | None = None,
    ) -> dict:
        endpoint = f"records/{record_id}/timeline"
        return await self._request(
            "POST",
            endpoint,
            displayName=display_name,
            start=start,
            description=description,
            type=type,
            private=private,
            categories=categories,
            customCategory=customCategory,
            metadata=metadata,
            end=end,
            projectId=projectId,
        )

    async def update_timeline_item(
        self,
        record_id: str,
        item_id: str,
        display_name: str,
        start: str,
        description: str | None = None,
        categories: str | None = None,
        private: bool | None = None,
        metadata: str | None = None,
        end: str | None = None,
    ) -> dict:
        endpoint = f"records/{record_id}/timeline/{item_id}"
        return await self._request(
            "PUT",
            endpoint,
            displayName=display_name,
            start=start,
            description=description,
            categories=categories,
            private=private,
            metadata=metadata,
            end=end,
        )

    async def delete_timeline_item(self, record_id: str, item_id: str) -> None:
        endpoint = f"records/{record_id}/timeline/{item_id}"
        await self._request("DELETE", endpoint)

    async def get_record_limits(self, record_id: str) -> list[dict]:
        endpoint = f"records/{record_id}/limits"
        return await self._request("GET", endpoint)

    async def get_record_benchmark(
        self,
        record_id: str,
        name: str,
        year: int,
        month: int | None = None,
    ) -> dict:
        endpoint = f"records/{record_id}/benchmark/{name}"
        return await self._request("GET", endpoint, year=year, month=month)

    async def get_record_benchmark_filtered(
        self,
        record_id: str,
        name: str,
        filter: str,
        year: int,
        month: int | None = None,
    ) -> dict:
        endpoint = f"records/{record_id}/benchmark/{name}/{filter}"
        return await self._request("GET", endpoint, year=year, month=month)

    async def _create_record(self, **kwargs) -> Record:
        d = await self._request("POST", "records", **kwargs)
        return Record(d, client=self)

    async def create_record(
        self,
        display_name: str,
        record_type: str,
        city: str,
        postal_code: str,
        country: str,
        category: str,
        street_address: str | None = None,
        tags: list[str] | None = None,
        dwelling_type: int | None = None,
        occupants: int | None = None,
        principal_residence: bool | None = None,
        heating_on: int | None = None,
        auxiliary_heating_on: int | None = None,
        hot_water_on: int | None = None,
        cooking_on: int | None = None,
        occupier_type: int | None = None,
        floor_surface: float | None = None,
        year_of_construction: int | None = None,
        year_of_renovation: int | None = None,
        energy_performance: float | None = None,
        energy_rating: float | None = None,
        energy_efficiency: int | None = None,
        installations: str | None = None,
        workspace_id: str | None = None,
        **kwargs,
    ) -> Record:
        return await self._create_record(
            displayName=display_name,
            recordType=record_type,
            city=city,
            postalCode=postal_code,
            country=country,
            category=category,
            streetAddress=street_address,
            tags=tags,
            dwellingType=dwelling_type,
            occupants=occupants,
            principalResidence=principal_residence,
            heatingOn=heating_on,
            auxiliaryHeatingOn=auxiliary_heating_on,
            hotWaterOn=hot_water_on,
            cookingOn=cooking_on,
            occupierType=occupier_type,
            floorSurface=floor_surface,
            yearOfConstruction=year_of_construction,
            yearOfRenovation=year_of_renovation,
            energyPerformance=energy_performance,
            energyRating=energy_rating,
            energyEfficiency=energy_efficiency,
            installations=installations,
            workspaceId=workspace_id,
            **kwargs,
        )

    async def edit_record(self, record_id: int, **kwargs) -> Record:
        endpoint = f"records/{record_id}"
        d = await self._request("PUT", endpoint, **kwargs)
        return Record(d, client=self)

    async def delete_record(self, record_id: int) -> None:
        endpoint = f"records/{record_id}"
        await self._request("DELETE", endpoint)

    async def get_record_definitions(self, record_id: str) -> list[dict]:
        endpoint = f"records/{record_id}/definitions"
        d = await self._request("GET", endpoint)
        return d["data"]
