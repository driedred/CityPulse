"""moderation pipeline audit fields

Revision ID: 20260403_0003
Revises: 20260403_0002
Create Date: 2026-04-03 01:15:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260403_0003"
down_revision: Union[str, Sequence[str], None] = "20260403_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

moderation_layer = sa.Enum(
    "deterministic",
    "llm",
    name="moderation_layer",
    native_enum=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    moderation_layer.create(bind, checkfirst=True)

    op.add_column(
        "moderation_results",
        sa.Column(
            "layer",
            moderation_layer,
            server_default="llm",
            nullable=False,
        ),
    )
    op.add_column(
        "moderation_results",
        sa.Column(
            "decision_code",
            sa.String(length=48),
            server_default="queued",
            nullable=False,
        ),
    )
    op.add_column(
        "moderation_results",
        sa.Column("machine_reasons", sa.JSON(), nullable=True),
    )
    op.add_column(
        "moderation_results",
        sa.Column("user_safe_explanation", sa.Text(), nullable=True),
    )
    op.add_column(
        "moderation_results",
        sa.Column("internal_notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "moderation_results",
        sa.Column(
            "escalation_required",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "moderation_results",
        sa.Column("normalized_category_slug", sa.String(length=80), nullable=True),
    )

    moderation_results = sa.table(
        "moderation_results",
        sa.column("status", sa.String(length=32)),
        sa.column("decision_code", sa.String(length=48)),
        sa.column("machine_reasons", sa.JSON()),
        sa.column("user_safe_explanation", sa.Text()),
        sa.column("internal_notes", sa.Text()),
        sa.column("escalation_required", sa.Boolean()),
    )
    op.execute(
        moderation_results.update().values(
            decision_code=sa.case(
                (
                    moderation_results.c.status == "approved",
                    sa.literal("approve"),
                ),
                (
                    moderation_results.c.status == "rejected",
                    sa.literal("reject"),
                ),
                (
                    moderation_results.c.status == "needs_review",
                    sa.literal("needs_manual_review"),
                ),
                else_=sa.literal("queued"),
            ),
            machine_reasons=sa.cast(sa.literal("[]"), sa.JSON()),
            user_safe_explanation=sa.null(),
            internal_notes=sa.literal("Migrated from pre-audit moderation schema."),
            escalation_required=sa.case(
                (
                    moderation_results.c.status == "needs_review",
                    sa.true(),
                ),
                else_=sa.false(),
            ),
        )
    )

    op.alter_column(
        "moderation_results",
        "machine_reasons",
        existing_type=sa.JSON(),
        nullable=False,
    )
    op.alter_column(
        "moderation_results",
        "layer",
        server_default=None,
        existing_type=moderation_layer,
    )
    op.alter_column(
        "moderation_results",
        "decision_code",
        server_default=None,
        existing_type=sa.String(length=48),
    )
    op.alter_column(
        "moderation_results",
        "escalation_required",
        server_default=None,
        existing_type=sa.Boolean(),
    )

    op.create_index(
        "ix_moderation_results_layer_status_created_at",
        "moderation_results",
        ["layer", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_moderation_results_layer_status_created_at",
        table_name="moderation_results",
    )
    op.drop_column("moderation_results", "normalized_category_slug")
    op.drop_column("moderation_results", "escalation_required")
    op.drop_column("moderation_results", "internal_notes")
    op.drop_column("moderation_results", "user_safe_explanation")
    op.drop_column("moderation_results", "machine_reasons")
    op.drop_column("moderation_results", "decision_code")
    op.drop_column("moderation_results", "layer")

    bind = op.get_bind()
    moderation_layer.drop(bind, checkfirst=True)
