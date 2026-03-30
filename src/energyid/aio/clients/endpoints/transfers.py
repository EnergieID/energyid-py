class TransfersMixin:
    async def create_transfer(
        self, record_id: str, email: str, remarks: str | None = None
    ) -> dict:
        return await self._request(
            "POST", "transfers", recordId=record_id, email=email, remarks=remarks
        )

    async def cancel_transfer(self, transfer_id: str) -> None:
        endpoint = f"transfers/{transfer_id}"
        await self._request("DELETE", endpoint)

    async def accept_transfer(self, transfer_id: str) -> dict:
        endpoint = f"transfers/{transfer_id}/accept"
        return await self._request("PUT", endpoint)

    async def decline_transfer(self, transfer_id: str) -> dict:
        endpoint = f"transfers/{transfer_id}/decline"
        return await self._request("PUT", endpoint)
