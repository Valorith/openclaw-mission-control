from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Generic, TypeVar

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import SelectOfScalar

ModelT = TypeVar("ModelT")


@dataclass(frozen=True)
class QuerySet(Generic[ModelT]):
    statement: SelectOfScalar[ModelT]

    def filter(self, *criteria: Any) -> QuerySet[ModelT]:
        return replace(self, statement=self.statement.where(*criteria))

    def where(self, *criteria: Any) -> QuerySet[ModelT]:
        return self.filter(*criteria)

    def filter_by(self, **kwargs: Any) -> QuerySet[ModelT]:
        statement = self.statement.filter_by(**kwargs)
        return replace(self, statement=statement)

    def order_by(self, *ordering: Any) -> QuerySet[ModelT]:
        return replace(self, statement=self.statement.order_by(*ordering))

    def limit(self, value: int) -> QuerySet[ModelT]:
        return replace(self, statement=self.statement.limit(value))

    def offset(self, value: int) -> QuerySet[ModelT]:
        return replace(self, statement=self.statement.offset(value))

    async def all(self, session: AsyncSession) -> list[ModelT]:
        return list(await session.exec(self.statement))

    async def first(self, session: AsyncSession) -> ModelT | None:
        return (await session.exec(self.statement)).first()

    async def one_or_none(self, session: AsyncSession) -> ModelT | None:
        return (await session.exec(self.statement)).one_or_none()

    async def exists(self, session: AsyncSession) -> bool:
        return await self.limit(1).first(session) is not None


def qs(model: type[ModelT]) -> QuerySet[ModelT]:
    return QuerySet(select(model))
