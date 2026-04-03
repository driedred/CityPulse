"""attachment image moderation preview storage

Revision ID: 20260403_0005
Revises: 20260403_0004
Create Date: 2026-04-03 04:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260403_0005"
down_revision: Union[str, Sequence[str], None] = "20260403_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "issue_attachments",
        sa.Column("moderation_image_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("issue_attachments", "moderation_image_url")
