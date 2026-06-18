"""
Shared CRUD helpers used across routers to eliminate duplicated
fetch-or-raise, partial-update, uniqueness-check, and create patterns.
"""
from __future__ import annotations

from typing import Any, Sequence, TypeVar

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import QueryableAttribute

from app.database import Base

ModelT = TypeVar("ModelT", bound=Base)


async def get_or_404(
    db: AsyncSession,
    model: type[ModelT],
    *filters: ColumnElement[bool],
    detail: str = "Not found",
    options: Sequence[Any] | None = None,
) -> ModelT:
    """
    Execute ``SELECT … WHERE *filters`` and return the single row,
    or raise HTTP 404 with *detail*.
    """
    query = select(model).where(*filters)
    if options:
        query = query.options(*options)
    result = await db.execute(query)
    instance = result.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return instance


async def apply_partial_update(
    db: AsyncSession,
    instance: Base,
    payload: BaseModel,
) -> None:
    """Apply non-None fields from a Pydantic schema onto a model instance."""
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(instance, field, value)
    await db.flush()
    await db.refresh(instance)


async def check_unique_or_409(
    db: AsyncSession,
    model: type[ModelT],
    *filters: ColumnElement[bool],
    detail: str = "Already exists",
) -> None:
    """Raise HTTP 409 if a row matching *filters* already exists."""
    result = await db.execute(select(model).where(*filters))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


async def create_and_refresh(db: AsyncSession, instance: Base) -> None:
    """``db.add`` + ``flush`` + ``refresh`` in one call."""
    db.add(instance)
    await db.flush()
    await db.refresh(instance)
