from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from sqlalchemy import false
from sqlmodel import SQLModel, col

from app.db.queryset import QuerySet, qs

ModelT = TypeVar("ModelT", bound=SQLModel)


@dataclass(frozen=True)
class ModelManager(Generic[ModelT]):
    model: type[ModelT]
    id_field: str = "id"

    def all(self) -> QuerySet[ModelT]:
        return qs(self.model)

    def none(self) -> QuerySet[ModelT]:
        return qs(self.model).filter(false())

    def filter(self, *criteria: Any) -> QuerySet[ModelT]:
        return self.all().filter(*criteria)

    def where(self, *criteria: Any) -> QuerySet[ModelT]:
        return self.filter(*criteria)

    def filter_by(self, **kwargs: Any) -> QuerySet[ModelT]:
        queryset = self.all()
        for field_name, value in kwargs.items():
            queryset = queryset.filter(col(getattr(self.model, field_name)) == value)
        return queryset

    def by_id(self, obj_id: Any) -> QuerySet[ModelT]:
        return self.by_field(self.id_field, obj_id)

    def by_ids(self, obj_ids: list[Any] | tuple[Any, ...] | set[Any]) -> QuerySet[ModelT]:
        return self.by_field_in(self.id_field, obj_ids)

    def by_field(self, field_name: str, value: Any) -> QuerySet[ModelT]:
        return self.filter(col(getattr(self.model, field_name)) == value)

    def by_field_in(
        self,
        field_name: str,
        values: list[Any] | tuple[Any, ...] | set[Any],
    ) -> QuerySet[ModelT]:
        seq = tuple(values)
        if not seq:
            return self.none()
        return self.filter(col(getattr(self.model, field_name)).in_(seq))


class ManagerDescriptor(Generic[ModelT]):
    def __get__(self, instance: object, owner: type[ModelT]) -> ModelManager[ModelT]:
        return ModelManager(owner)
