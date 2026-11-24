"""levels and progression for study topics and subjects

Revision ID: 004
Revises: 003
Create Date: 2026-11-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "study_topics",
        sa.Column("level", sa.String(20), nullable=False, server_default="iniciante"),
    )
    op.add_column(
        "study_topics",
        sa.Column(
            "unlocked_manual", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "subjects",
        sa.Column("level", sa.String(20), nullable=False, server_default="iniciante"),
    )
    op.add_column(
        "subjects",
        sa.Column(
            "unlocked_manual", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "subjects",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("subjects", "sort_order")
    op.drop_column("subjects", "unlocked_manual")
    op.drop_column("subjects", "level")
    op.drop_column("study_topics", "unlocked_manual")
    op.drop_column("study_topics", "level")
