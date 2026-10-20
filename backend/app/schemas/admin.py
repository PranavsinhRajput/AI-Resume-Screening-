from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AdminUser(BaseModel):
    id: str
    email: str | None = None
    role: Literal["user", "admin"]
    status: Literal["pending", "approved", "rejected"]
    created_at: datetime
    reviewed_at: datetime | None = None
    last_sign_in_at: datetime | None = None
    resume_count: int = 0
    done_count: int = 0


class AdminStats(BaseModel):
    pending: int
    approved: int
    rejected: int
