from __future__ import annotations
from contextlib import contextmanager

from psycopg_pool import ConnectionPool


DATABASE_URL = "postgres://271a298019f6bdfd663a2c0718cc52c723541e747b79fa79b4f940098230e7d8:sk_PGpudX7pHQwX2_dD5woeT@db.prisma.io:5432/postgres?sslmode=require"

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")


_pool = ConnectionPool(conninfo=DATABASE_URL, min_size=1, max_size=10)


@contextmanager
def get_connection():
    """Provide a pooled database connection."""

    with _pool.connection() as connection:
        yield connection