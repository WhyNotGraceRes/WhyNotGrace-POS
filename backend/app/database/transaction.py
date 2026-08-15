"""Explicit transaction boundary helper.

Use as a context manager around multi-step writes (e.g. order creation,
billing, payment capture) so a failure partway through rolls back cleanly
instead of leaving partial state.
"""
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session


@contextmanager
def transaction(db: Session) -> Iterator[Session]:
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
