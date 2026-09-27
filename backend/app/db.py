import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


class DatabaseNotConfiguredError(RuntimeError):
    pass


def _database_url() -> str:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        raise DatabaseNotConfiguredError("DATABASE_URL is not configured")
    return value


_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=_database_url(),
            min_size=1,
            max_size=10,
            timeout=5,
            kwargs={"row_factory": dict_row, "connect_timeout": 5},
            open=True,
        )
    return _pool


@contextmanager
def connection() -> Iterator:
    with get_pool().connection() as conn:
        yield conn


def initialize_database() -> None:
    migration = Path(__file__).resolve().parents[1] / "migrations" / "001_initial.sql"
    with psycopg.connect(_database_url(), connect_timeout=5) as conn:
        conn.execute(migration.read_text(encoding="utf-8"))
        conn.commit()


def close_database() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
