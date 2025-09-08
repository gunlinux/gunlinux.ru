"""Base repository interface for the application."""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional

T = TypeVar("T")  # Domain model type
ID = TypeVar("ID")  # ID type


class BaseRepository(ABC, Generic[T, ID]):
    """Abstract base class for all repositories."""

    @abstractmethod
    def get_by_id(self, id: ID) -> Optional[T]:
        """Get an entity by its ID."""
        pass

    @abstractmethod
    def get_all(self) -> List[T]:
        """Get all entities."""
        pass

    @abstractmethod
    def create(self, entity: T) -> T:
        """Create a new entity."""
        pass

    @abstractmethod
    def update(self, entity: T) -> T:
        """Update an existing entity."""
        pass

    @abstractmethod
    def delete(self, id: ID) -> bool:
        """Delete an entity by its ID."""
        pass
