from contextlib import AbstractContextManager
from typing import Optional

from sqlalchemy.orm import Session

from hopilot.database import DatabaseConnection
from hopilot.logging_config import get_logger

logger = get_logger(__name__)


class UnitOfWork(AbstractContextManager["UnitOfWork"]):
    """Shared session/unit-of-work helper for coupled repository writes."""

    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection
        self._session: Optional[Session] = None
        self._transaction = None

    def __enter__(self) -> "UnitOfWork":
        self._session = self.db_connection.get_session()
        self._transaction = self._session.begin()
        logger.debug("UnitOfWork session started")
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        try:
            if exc_type is None:
                self._transaction.commit()
                logger.debug("UnitOfWork transaction committed")
            else:
                self._transaction.rollback()
                logger.debug("UnitOfWork transaction rolled back due to exception")
        finally:
            if self._session is not None:
                self._session.close()
                logger.debug("UnitOfWork session closed")
        return False

    @property
    def session(self) -> Session:
        if self._session is None:
            raise RuntimeError("UnitOfWork session is not initialized")
        return self._session

    def commit(self) -> None:
        if self._transaction is not None and self._transaction.is_active:
            self._transaction.commit()

    def rollback(self) -> None:
        if self._transaction is not None and self._transaction.is_active:
            self._transaction.rollback()