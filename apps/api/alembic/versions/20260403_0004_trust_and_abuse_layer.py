"""trust score snapshots and anti-abuse event log

Revision ID: 20260403_0004
Revises: 20260403_0003
Create Date: 2026-04-03 02:40:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260403_0004"
down_revision: Union[str, Sequence[str], None] = "20260403_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

abuse_risk_level = sa.Enum(
    "low",
    "medium",
    "high",
    name="abuse_risk_level",
    native_enum=False,
)
integrity_event_severity = sa.Enum(
    "low",
    "medium",
    "high",
    name="integrity_event_severity",
    native_enum=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    abuse_risk_level.create(bind, checkfirst=True)
    integrity_event_severity.create(bind, checkfirst=True)

    op.create_table(
        "user_integrity_snapshots",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("trust_score", sa.Float(), nullable=False),
        sa.Column("trust_weight_multiplier", sa.Float(), nullable=False),
        sa.Column("abuse_risk_level", abuse_risk_level, nullable=False),
        sa.Column("abuse_risk_score", sa.Float(), nullable=False),
        sa.Column("sanction_count", sa.Integer(), nullable=False),
        sa.Column("trust_breakdown", sa.JSON(), nullable=False),
        sa.Column("abuse_summary", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(
        "ix_user_integrity_snapshots_trust_score",
        "user_integrity_snapshots",
        ["trust_score"],
        unique=False,
    )
    op.create_index(
        "ix_user_integrity_snapshots_abuse_risk_level",
        "user_integrity_snapshots",
        ["abuse_risk_level"],
        unique=False,
    )
    op.create_index(
        "ix_user_integrity_snapshots_updated_at",
        "user_integrity_snapshots",
        ["updated_at"],
        unique=False,
    )

    op.create_table(
        "integrity_events",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("severity", integrity_event_severity, nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("ip_hash", sa.String(length=128), nullable=True),
        sa.Column("device_fingerprint_hash", sa.String(length=128), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_integrity_events_user_created_at",
        "integrity_events",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_integrity_events_type_created_at",
        "integrity_events",
        ["event_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_integrity_events_severity_created_at",
        "integrity_events",
        ["severity", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_integrity_events_severity_created_at", table_name="integrity_events")
    op.drop_index("ix_integrity_events_type_created_at", table_name="integrity_events")
    op.drop_index("ix_integrity_events_user_created_at", table_name="integrity_events")
    op.drop_table("integrity_events")

    op.drop_index(
        "ix_user_integrity_snapshots_updated_at",
        table_name="user_integrity_snapshots",
    )
    op.drop_index(
        "ix_user_integrity_snapshots_abuse_risk_level",
        table_name="user_integrity_snapshots",
    )
    op.drop_index(
        "ix_user_integrity_snapshots_trust_score",
        table_name="user_integrity_snapshots",
    )
    op.drop_table("user_integrity_snapshots")

    bind = op.get_bind()
    integrity_event_severity.drop(bind, checkfirst=True)
    abuse_risk_level.drop(bind, checkfirst=True)
