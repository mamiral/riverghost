"""
Base SQLAlchemy model class for poker analysis database.

Provides common functionality for all database models including
timestamps, serialization, and validation.
"""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Integer, MetaData
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

from hopilot.logging_config import get_logger

logger = get_logger(__name__)

# Naming convention for constraints and indexes
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Create metadata with naming convention
metadata = MetaData(naming_convention=convention)

# Create declarative base
Base = declarative_base(metadata=metadata)


class BaseModel(Base):
    """
    Base model class with common functionality.

    Provides:
    - Auto-incrementing primary key
    - Automatic timestamps (created_at, updated_at)
    - Serialization methods
    - Validation hooks
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __init__(self, **kwargs):
        """Initialize model with validation."""
        super().__init__(**kwargs)
        self._validate()

    def _validate(self) -> None:
        """
        Validate model data.

        Override in subclasses to add custom validation.
        Raise ValueError for validation errors.
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model to dictionary.

        Returns:
            Dictionary representation of the model
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                # Convert datetime to ISO format string
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result

    def to_json(self) -> str:
        """
        Serialize model to JSON string.

        Returns:
            JSON string representation of the model
        """
        import json
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        Create model instance from dictionary.

        Args:
            data: Dictionary with model data

        Returns:
            New model instance
        """
        # Remove any computed fields that aren't actual columns
        column_names = {column.name for column in cls.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in column_names}
        return cls(**filtered_data)

    @classmethod
    def from_json(cls, json_str: str):
        """
        Deserialize model from JSON string.

        Args:
            json_str: JSON string representation

        Returns:
            New model instance
        """
        import json
        data = json.loads(json_str)
        return cls.from_dict(data)

    def to_pickle(self) -> bytes:
        """
        Serialize model to pickle bytes for efficient storage.
        
        This provides faster serialization/deserialization than JSON
        with minimal overhead for SIM-002 requirements.
        
        Returns:
            Pickle bytes representation of the model
        """
        import pickle
        return pickle.dumps(self.to_dict())

    @classmethod
    def from_pickle(cls, pickle_bytes: bytes):
        """
        Deserialize model from pickle bytes.

        Args:
            pickle_bytes: Pickle bytes representation

        Returns:
            New model instance
        """
        import pickle
        data = pickle.loads(pickle_bytes)
        return cls.from_dict(data)

    def to_compressed_pickle(self) -> bytes:
        """
        Serialize model to compressed pickle for storage efficiency.
        
        Uses gzip compression to minimize storage overhead while
        maintaining fast serialization/deserialization.
        
        Returns:
            Compressed pickle bytes
        """
        import gzip
        import pickle
        data = self.to_dict()
        return gzip.compress(pickle.dumps(data))

    @classmethod
    def from_compressed_pickle(cls, compressed_bytes: bytes):
        """
        Deserialize model from compressed pickle bytes.

        Args:
            compressed_bytes: Compressed pickle bytes

        Returns:
            New model instance
        """
        import gzip
        import pickle
        data = pickle.loads(gzip.decompress(compressed_bytes))
        return cls.from_dict(data)

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update model from dictionary.

        Args:
            data: Dictionary with field updates
        """
        for key, value in data.items():
            if hasattr(self, key) and key != 'id':
                setattr(self, key, value)
        self._validate()

    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"

    @classmethod
    def get_by_id(cls, session, model_id: int):
        """
        Get model instance by ID.

        Args:
            session: SQLAlchemy session
            model_id: Primary key value

        Returns:
            Model instance or None
        """
        return session.query(cls).filter(cls.id == model_id).first()

    @classmethod
    def create(cls, session, **kwargs):
        """
        Create and save a new model instance.

        Args:
            session: SQLAlchemy session
            **kwargs: Model field values

        Returns:
            Created model instance
        """
        instance = cls(**kwargs)
        session.add(instance)
        session.flush()  # Get ID without committing
        logger.debug(f"Created {cls.__name__}: {instance}")
        return instance

    @classmethod
    def bulk_create(cls, session, instances_data: list) -> list:
        """
        Bulk create multiple model instances.

        Args:
            session: SQLAlchemy session
            instances_data: List of dictionaries with field values

        Returns:
            List of created model instances
        """
        instances = [cls(**data) for data in instances_data]
        session.add_all(instances)
        session.flush()
        logger.debug(f"Bulk created {len(instances)} {cls.__name__} instances")
        return instances