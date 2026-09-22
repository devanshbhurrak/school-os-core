from __future__ import annotations

from pydantic import BaseModel


class PlatformStats(BaseModel):
    org_count: int
    school_count: int
    user_count: int
