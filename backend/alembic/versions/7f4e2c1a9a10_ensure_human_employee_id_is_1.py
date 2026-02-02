"""Ensure human employee id is 1

Revision ID: 7f4e2c1a9a10
Revises: 3f2c1b9c8e12
Create Date: 2026-02-02

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7f4e2c1a9a10"
down_revision = "3f2c1b9c8e12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """If the (single) human employee exists but is not id=1, move it to id=1.

    This is a dev ergonomics migration: a bunch of code / examples assume the
    primary human user is employee_id=1.

    Safe behavior:
    - Only runs when there is exactly one human employee.
    - Only runs when employee id=1 is currently unused.
    - Rewrites all known FKs that point at the old id.
    """

    conn = op.get_bind()

    human_ids = [
        row[0]
        for row in conn.execute(sa.text("SELECT id FROM employees WHERE employee_type='human' ORDER BY id"))
    ]

    # Only attempt the rewrite in the "typical dev" scenario.
    if len(human_ids) != 1:
        return

    old_id = int(human_ids[0])
    if old_id == 1:
        return

    id1_exists = conn.execute(sa.text("SELECT 1 FROM employees WHERE id=1")).first() is not None
    if id1_exists:
        return

    # Update foreign keys in known tables/columns.
    conn.execute(
        sa.text("UPDATE departments SET head_employee_id=1 WHERE head_employee_id=:old_id"),
        {"old_id": old_id},
    )
    conn.execute(
        sa.text("UPDATE teams SET lead_employee_id=1 WHERE lead_employee_id=:old_id"),
        {"old_id": old_id},
    )
    conn.execute(
        sa.text("UPDATE employees SET manager_id=1 WHERE manager_id=:old_id"),
        {"old_id": old_id},
    )
    conn.execute(
        sa.text("UPDATE activities SET actor_employee_id=1 WHERE actor_employee_id=:old_id"),
        {"old_id": old_id},
    )
    conn.execute(
        sa.text("UPDATE project_members SET employee_id=1 WHERE employee_id=:old_id"),
        {"old_id": old_id},
    )
    conn.execute(
        sa.text("UPDATE tasks SET assignee_employee_id=1 WHERE assignee_employee_id=:old_id"),
        {"old_id": old_id},
    )
    conn.execute(
        sa.text("UPDATE tasks SET reviewer_employee_id=1 WHERE reviewer_employee_id=:old_id"),
        {"old_id": old_id},
    )
    conn.execute(
        sa.text("UPDATE tasks SET created_by_employee_id=1 WHERE created_by_employee_id=:old_id"),
        {"old_id": old_id},
    )
    conn.execute(
        sa.text("UPDATE task_comments SET author_employee_id=1 WHERE author_employee_id=:old_id"),
        {"old_id": old_id},
    )

    # Finally, rewrite the employee PK itself.
    conn.execute(sa.text("UPDATE employees SET id=1 WHERE id=:old_id"), {"old_id": old_id})

    # Keep the sequence in sync (Postgres).
    conn.execute(
        sa.text(
            "SELECT setval(pg_get_serial_sequence('employees','id'), (SELECT COALESCE(MAX(id), 1) FROM employees), true)"
        )
    )


def downgrade() -> None:
    # Non-reversible in a safe way; this is a dev convenience migration.
    pass
