from enum import Enum


class Scope(Enum):
    RECORDS_WRITE = "records:write"
    RECORDS_READ = "records:read"
    PROFILE_WRITE = "profile:write"
    PROFILE_READ = "profile:read"
    GROUPS_WRITE = "groups:write"
    GROUPS_READ = "groups:read"
