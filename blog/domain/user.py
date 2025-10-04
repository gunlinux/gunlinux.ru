"""Domain models for the User entity."""

from typing import override
import datetime
from dataclasses import dataclass


@dataclass
class User:
    """Domain model for user."""

    id: int | None = None
    name: str = ""
    password: str = ""
    authenticated: bool = False
    createdon: datetime.datetime | None = None

    def __post_init__(self):
        if self.createdon is None:
            self.createdon = datetime.datetime.now(datetime.timezone.utc)

    @override
    def __str__(self):
        return f"{self.name}"
