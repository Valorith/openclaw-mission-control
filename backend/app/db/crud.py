from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, TypeVar

from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import SelectOfScalar

ModelT = TypeVar("ModelT", bound=SQLModel)


class DoesNotExist(LookupError):
    pass


class MultipleObjectsReturned(LookupError):
    pass


def _lookup_statement(model: type[ModelT], lookup: Mapping[str, Any]) -> SelectOfScalar[ModelT]:
    stmt = select(model)
    for key, value in lookup.items():
        stmt = stmt.where(getattr(model, key) == value)
    return stmt


async def get_by_id(session: AsyncSession, model: type[ModelT], obj_id: Any) -> ModelT | None:
    stmt = _lookup_statement(model, {"id": obj_id}).limit(1)
    return (await session.exec(stmt)).first()


async def get(session: AsyncSession, model: type[ModelT], **lookup: Any) -> ModelT:
    stmt = _lookup_statement(model, lookup).limit(2)
    items = (await session.exec(stmt)).all()
    if not items:
        raise DoesNotExist(f"{model.__name__} matching query does not exist.")
    if len(items) > 1:
        raise MultipleObjectsReturned(
            f"Multiple {model.__name__} objects returned for lookup {lookup!r}."
        )
    return items[0]


async def get_one_by(session: AsyncSession, model: type[ModelT], **lookup: Any) -> ModelT | None:
    stmt = _lookup_statement(model, lookup)
    return (await session.exec(stmt)).first()


async def create(
    session: AsyncSession,
    model: type[ModelT],
    *,
    commit: bool = True,
    refresh: bool = True,
    **data: Any,
) -> ModelT:
    obj = model.model_validate(data)
    session.add(obj)
    await session.flush()
    if commit:
        await session.commit()
    if refresh:
        await session.refresh(obj)
    return obj


async def save(
    session: AsyncSession,
    obj: ModelT,
    *,
    commit: bool = True,
    refresh: bool = True,
) -> ModelT:
    session.add(obj)
    await session.flush()
    if commit:
        await session.commit()
    if refresh:
        await session.refresh(obj)
    return obj


async def delete(session: AsyncSession, obj: ModelT, *, commit: bool = True) -> None:
    await session.delete(obj)
    if commit:
        await session.commit()


async def list_by(
    session: AsyncSession,
    model: type[ModelT],
    *,
    order_by: Iterable[Any] = (),
    limit: int | None = None,
    offset: int | None = None,
    **lookup: Any,
) -> list[ModelT]:
    stmt = _lookup_statement(model, lookup)
    for ordering in order_by:
        stmt = stmt.order_by(ordering)
    if offset is not None:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(await session.exec(stmt))


async def exists(session: AsyncSession, model: type[ModelT], **lookup: Any) -> bool:
    return (await session.exec(_lookup_statement(model, lookup).limit(1))).first() is not None


def apply_updates(
    obj: ModelT,
    updates: Mapping[str, Any],
    *,
    exclude_none: bool = False,
    allowed_fields: set[str] | None = None,
) -> ModelT:
    for key, value in updates.items():
        if allowed_fields is not None and key not in allowed_fields:
            continue
        if exclude_none and value is None:
            continue
        setattr(obj, key, value)
    return obj


async def patch(
    session: AsyncSession,
    obj: ModelT,
    updates: Mapping[str, Any],
    *,
    exclude_none: bool = False,
    allowed_fields: set[str] | None = None,
    commit: bool = True,
    refresh: bool = True,
) -> ModelT:
    apply_updates(
        obj,
        updates,
        exclude_none=exclude_none,
        allowed_fields=allowed_fields,
    )
    return await save(session, obj, commit=commit, refresh=refresh)


async def get_or_create(
    session: AsyncSession,
    model: type[ModelT],
    *,
    defaults: Mapping[str, Any] | None = None,
    commit: bool = True,
    refresh: bool = True,
    **lookup: Any,
) -> tuple[ModelT, bool]:
    stmt = _lookup_statement(model, lookup)

    existing = (await session.exec(stmt)).first()
    if existing is not None:
        return existing, False

    payload: dict[str, Any] = dict(lookup)
    if defaults:
        for key, value in defaults.items():
            payload.setdefault(key, value)

    obj = model.model_validate(payload)
    session.add(obj)
    try:
        await session.flush()
        if commit:
            await session.commit()
    except IntegrityError:
        # If another concurrent request inserted the same unique row, surface that row.
        await session.rollback()
        existing = (await session.exec(stmt)).first()
        if existing is not None:
            return existing, False
        raise

    if refresh:
        await session.refresh(obj)
    return obj, True
