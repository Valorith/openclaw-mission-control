from __future__ import annotations

from app.models.base import QueryModel


class TenantScoped(QueryModel, table=False):
    pass
