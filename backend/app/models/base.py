from __future__ import annotations

from typing import ClassVar, Self

from sqlmodel import SQLModel

from app.db.query_manager import ManagerDescriptor


class QueryModel(SQLModel, table=False):
    objects: ClassVar[ManagerDescriptor[Self]] = ManagerDescriptor()
