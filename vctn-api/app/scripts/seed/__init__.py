"""Idempotent PostgreSQL seed data for the VCTN backend.

Run with::

    python -m app.scripts.seed                # system (production) seed
    python -m app.scripts.seed --mode=test    # system seed + test data

The seed only ever inserts rows whose stable business key is missing. It never
truncates, drops, deletes, rewrites an existing row or resets an existing
password, so it is safe to run repeatedly and safe to run against a populated
database.
"""

from app.scripts.seed.errors import SeedError

__all__ = ["SeedError"]
