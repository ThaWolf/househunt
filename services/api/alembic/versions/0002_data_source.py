"""Add properties.data_source for listing fidelity (iter 4).

Revision ID: 0002_data_source
Revises: 0001_initial
Create Date: 2026-07-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_data_source"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "properties",
        sa.Column("data_source", sa.String(length=32), nullable=False, server_default="live"),
    )


def downgrade() -> None:
    op.drop_column("properties", "data_source")
