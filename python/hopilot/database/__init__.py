"""Database package exports for the shared SQLAlchemy connection layer."""

from __future__ import annotations

import importlib.util
from pathlib import Path


_DATABASE_MODULE_PATH = Path(__file__).resolve().parent.parent / "database.py"
_SPEC = importlib.util.spec_from_file_location("hopilot._database_module", _DATABASE_MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:
	raise ImportError(f"Unable to load database module from {_DATABASE_MODULE_PATH}")

_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

ConnectionError = _MODULE.ConnectionError
DataValidationError = _MODULE.DataValidationError
DatabaseConnection = _MODULE.DatabaseConnection
DatabaseError = _MODULE.DatabaseError
IntegrityError = _MODULE.IntegrityError
get_database_connection = _MODULE.get_database_connection

__all__ = [
	"ConnectionError",
	"DataValidationError",
	"DatabaseConnection",
	"DatabaseError",
	"IntegrityError",
	"get_database_connection",
]