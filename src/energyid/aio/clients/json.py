from .base import BaseClient
from .endpoints import (
    CatalogsMixin,
    GroupsMixin,
    MembersMixin,
    MetersMixin,
    OrganizationsMixin,
    RecordsMixin,
    SearchMixin,
    TransfersMixin,
)


class JSONClient(
    CatalogsMixin,
    GroupsMixin,
    MembersMixin,
    MetersMixin,
    OrganizationsMixin,
    RecordsMixin,
    SearchMixin,
    TransfersMixin,
    BaseClient,
):
    """Async JSON API client."""

    pass
