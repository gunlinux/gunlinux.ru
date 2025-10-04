"""Factory for creating ORM adapters."""

from blog.adapters.orm_adapter import ORMAdapter


class ORMAdapterFactory:
    """Factory for creating ORM adapters."""

    @staticmethod
    def create_orm_adapter():
        """Create an ORM adapter instance."""
        return ORMAdapter()
