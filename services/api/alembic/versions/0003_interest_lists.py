"""Shared interest lists — migrate per-user items/visits to list scope.

Revision ID: 0003_interest_lists
Revises: 0002_data_source
Create Date: 2026-07-16
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0003_interest_lists"
down_revision = "0002_data_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interest_lists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False, server_default="Mi lista"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interest_lists_owner_user_id", "interest_lists", ["owner_user_id"])

    op.create_table(
        "interest_list_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("list_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["list_id"], ["interest_lists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("list_id", "user_id", name="uq_list_member"),
    )
    op.create_index("ix_interest_list_members_list_id", "interest_list_members", ["list_id"])
    op.create_index("ix_interest_list_members_user_id", "interest_list_members", ["user_id"])

    op.add_column("interest_items", sa.Column("list_id", sa.Uuid(), nullable=True))
    op.add_column("interest_items", sa.Column("added_by_user_id", sa.Uuid(), nullable=True))
    op.add_column("visits", sa.Column("list_id", sa.Uuid(), nullable=True))

    conn = op.get_bind()
    user_rows = conn.execute(
        sa.text(
            """
            SELECT DISTINCT user_id FROM interest_items
            UNION
            SELECT DISTINCT user_id FROM visits
            """
        )
    ).fetchall()

    for (user_id,) in user_rows:
        list_id = uuid.uuid4()
        conn.execute(
            sa.text(
                """
                INSERT INTO interest_lists (id, owner_user_id, name)
                VALUES (:list_id, :user_id, 'Mi lista')
                """
            ),
            {"list_id": list_id, "user_id": user_id},
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO interest_list_members (id, list_id, user_id, role)
                VALUES (:id, :list_id, :user_id, 'owner')
                """
            ),
            {"id": uuid.uuid4(), "list_id": list_id, "user_id": user_id},
        )
        conn.execute(
            sa.text(
                """
                UPDATE interest_items
                SET list_id = :list_id, added_by_user_id = user_id
                WHERE user_id = :user_id
                """
            ),
            {"list_id": list_id, "user_id": user_id},
        )
        conn.execute(
            sa.text(
                """
                UPDATE visits SET list_id = :list_id WHERE user_id = :user_id
                """
            ),
            {"list_id": list_id, "user_id": user_id},
        )

    op.drop_constraint("uq_user_property_interest", "interest_items", type_="unique")
    op.drop_index("ix_interest_items_user_id", table_name="interest_items")
    op.drop_constraint("interest_items_user_id_fkey", "interest_items", type_="foreignkey")
    op.drop_column("interest_items", "user_id")

    op.create_foreign_key(
        "interest_items_list_id_fkey",
        "interest_items",
        "interest_lists",
        ["list_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "interest_items_added_by_user_id_fkey",
        "interest_items",
        "users",
        ["added_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_interest_items_list_id", "interest_items", ["list_id"])
    op.create_unique_constraint(
        "uq_list_property_interest", "interest_items", ["list_id", "property_id"]
    )
    op.alter_column("interest_items", "list_id", nullable=False)
    op.alter_column("interest_items", "added_by_user_id", nullable=False)

    op.drop_constraint("uq_user_property_visit", "visits", type_="unique")
    op.drop_index("ix_visits_user_id", table_name="visits")
    op.drop_constraint("visits_user_id_fkey", "visits", type_="foreignkey")
    op.drop_column("visits", "user_id")

    op.create_foreign_key(
        "visits_list_id_fkey", "visits", "interest_lists", ["list_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_visits_list_id", "visits", ["list_id"])
    op.create_unique_constraint("uq_list_property_visit", "visits", ["list_id", "property_id"])
    op.alter_column("visits", "list_id", nullable=False)


def downgrade() -> None:
    op.add_column("interest_items", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.add_column("visits", sa.Column("user_id", sa.Uuid(), nullable=True))

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE interest_items ii
            SET user_id = il.owner_user_id
            FROM interest_lists il
            WHERE ii.list_id = il.id
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE visits v
            SET user_id = il.owner_user_id
            FROM interest_lists il
            WHERE v.list_id = il.id
            """
        )
    )

    op.drop_constraint("uq_list_property_visit", "visits", type_="unique")
    op.drop_index("ix_visits_list_id", table_name="visits")
    op.drop_constraint("visits_list_id_fkey", "visits", type_="foreignkey")
    op.drop_column("visits", "list_id")
    op.create_foreign_key(
        "visits_user_id_fkey", "visits", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_visits_user_id", "visits", ["user_id"])
    op.create_unique_constraint("uq_user_property_visit", "visits", ["user_id", "property_id"])
    op.alter_column("visits", "user_id", nullable=False)

    op.drop_constraint("uq_list_property_interest", "interest_items", type_="unique")
    op.drop_index("ix_interest_items_list_id", table_name="interest_items")
    op.drop_constraint("interest_items_list_id_fkey", "interest_items", type_="foreignkey")
    op.drop_constraint(
        "interest_items_added_by_user_id_fkey", "interest_items", type_="foreignkey"
    )
    op.drop_column("interest_items", "list_id")
    op.drop_column("interest_items", "added_by_user_id")
    op.create_foreign_key(
        "interest_items_user_id_fkey",
        "interest_items",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_interest_items_user_id", "interest_items", ["user_id"])
    op.create_unique_constraint(
        "uq_user_property_interest", "interest_items", ["user_id", "property_id"]
    )
    op.alter_column("interest_items", "user_id", nullable=False)

    op.drop_table("interest_list_members")
    op.drop_table("interest_lists")
