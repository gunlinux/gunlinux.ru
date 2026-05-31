import datetime
from dataclasses import dataclass
from typing import override


@dataclass
class User:
    id: int | None = None
    name: str = ""
    password: str = ""
    authenticated: bool = False
    createdon: datetime.datetime | None = None

    def __post_init__(self):
        if self.createdon is None:
            self.createdon = datetime.datetime.now(datetime.timezone.utc)

    @override
    def __str__(self) -> str:
        return f"{self.name}"
