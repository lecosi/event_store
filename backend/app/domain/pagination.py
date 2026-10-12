"""Generic page of results shared by every paginated query."""

from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        return ceil(self.total / self.size) if self.total else 0
