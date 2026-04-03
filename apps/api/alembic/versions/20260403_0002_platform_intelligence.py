"""platform intelligence tables and scoring baselines

Revision ID: 20260403_0002
Revises: 20260403_0001
Create Date: 2026-04-03 00:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260403_0002"
down_revision: Union[str, Sequence[str], None] = "20260403_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

old_swipe_direction = sa.Enum(
    "support",
    "skip",
    "dismiss",
    name="swipe_direction",
    native_enum=False,
)
new_swipe_direction = sa.Enum(
    "support",
    "skip",
    "more_like_this",
    "less_like_this",
    name="swipe_direction",
    native_enum=False,
)
duplicate_resolution_status = sa.Enum(
    "possible",
    "confirmed",
    "supported_existing",
    "dismissed",
    name="duplicate_resolution_status",
    native_enum=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    duplicate_resolution_status.create(bind, checkfirst=True)

    op.add_column(
        "issue_categories",
        sa.Column(
            "severity_baseline",
            sa.Float(),
            server_default=sa.text("0.5"),
            nullable=False,
        ),
    )
    op.add_column(
        "issue_categories",
        sa.Column(
            "affected_people_baseline",
            sa.Integer(),
            server_default=sa.text("20"),
            nullable=False,
        ),
    )

    op.execute(
        """
        UPDATE issue_categories
        SET severity_baseline = CASE slug
            WHEN 'roads' THEN 0.72
            WHEN 'sanitation' THEN 0.58
            WHEN 'lighting' THEN 0.64
            WHEN 'safety' THEN 0.86
            WHEN 'transport' THEN 0.68
            ELSE 0.5
        END,
        affected_people_baseline = CASE slug
            WHEN 'roads' THEN 45
            WHEN 'sanitation' THEN 35
            WHEN 'lighting' THEN 28
            WHEN 'safety' THEN 70
            WHEN 'transport' THEN 55
            ELSE 20
        END
        """
    )

    op.alter_column(
        "issue_categories",
        "severity_baseline",
        server_default=None,
        existing_type=sa.Float(),
    )
    op.alter_column(
        "issue_categories",
        "affected_people_baseline",
        server_default=None,
        existing_type=sa.Integer(),
    )

    op.execute(
        "ALTER TABLE swipe_feedback DROP CONSTRAINT IF EXISTS ck_swipe_feedback_swipe_direction"
    )
    op.alter_column(
        "swipe_feedback",
        "direction",
        existing_type=old_swipe_direction,
        type_=new_swipe_direction,
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_swipe_feedback_swipe_direction",
        "swipe_feedback",
        "direction IN ('support', 'skip', 'more_like_this', 'less_like_this')",
    )

    op.create_table(
        "issue_impact_snapshots",
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("public_impact_score", sa.Float(), nullable=False),
        sa.Column("affected_people_estimate", sa.Integer(), nullable=False),
        sa.Column("score_version", sa.String(length=32), nullable=False),
        sa.Column("signals", sa.JSON(), nullable=False),
        sa.Column("breakdown", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issue_id"),
    )
    op.create_index(
        "ix_issue_impact_snapshots_public_score",
        "issue_impact_snapshots",
        ["public_impact_score"],
        unique=False,
    )
    op.create_index(
        "ix_issue_impact_snapshots_updated_at",
        "issue_impact_snapshots",
        ["updated_at"],
        unique=False,
    )

    op.create_table(
        "issue_duplicate_links",
        sa.Column("canonical_issue_id", sa.Uuid(), nullable=False),
        sa.Column("duplicate_issue_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("status", duplicate_resolution_status, nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("distance_km", sa.Float(), nullable=True),
        sa.Column("text_similarity", sa.Float(), nullable=True),
        sa.Column("category_match", sa.Boolean(), nullable=False),
        sa.Column("reason_breakdown", sa.JSON(), nullable=False),
        sa.Column("candidate_snapshot", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["canonical_issue_id"], ["issues.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["duplicate_issue_id"], ["issues.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "canonical_issue_id",
            "duplicate_issue_id",
            name="uq_issue_duplicate_links_canonical_duplicate",
        ),
    )
    op.create_index(
        "ix_issue_duplicate_links_canonical_status",
        "issue_duplicate_links",
        ["canonical_issue_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_issue_duplicate_links_duplicate_status",
        "issue_duplicate_links",
        ["duplicate_issue_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_issue_duplicate_links_duplicate_status",
        table_name="issue_duplicate_links",
    )
    op.drop_index(
        "ix_issue_duplicate_links_canonical_status",
        table_name="issue_duplicate_links",
    )
    op.drop_table("issue_duplicate_links")

    op.drop_index(
        "ix_issue_impact_snapshots_updated_at",
        table_name="issue_impact_snapshots",
    )
    op.drop_index(
        "ix_issue_impact_snapshots_public_score",
        table_name="issue_impact_snapshots",
    )
    op.drop_table("issue_impact_snapshots")

    op.execute(
        "ALTER TABLE swipe_feedback DROP CONSTRAINT IF EXISTS ck_swipe_feedback_swipe_direction"
    )
    op.alter_column(
        "swipe_feedback",
        "direction",
        existing_type=new_swipe_direction,
        type_=old_swipe_direction,
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_swipe_feedback_swipe_direction",
        "swipe_feedback",
        "direction IN ('support', 'skip', 'dismiss')",
    )

    op.drop_column("issue_categories", "affected_people_baseline")
    op.drop_column("issue_categories", "severity_baseline")

    bind = op.get_bind()
    duplicate_resolution_status.drop(bind, checkfirst=True)
