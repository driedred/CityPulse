"""initial citypulse schema

Revision ID: 20260403_0001
Revises:
Create Date: 2026-04-03 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260403_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = sa.Enum("citizen", "admin", name="user_role", native_enum=False)
issue_status = sa.Enum(
    "draft",
    "pending_moderation",
    "approved",
    "rejected",
    "published",
    "archived",
    name="issue_status",
    native_enum=False,
)
moderation_state = sa.Enum(
    "not_requested",
    "queued",
    "under_review",
    "completed",
    name="moderation_state",
    native_enum=False,
)
swipe_direction = sa.Enum(
    "support",
    "skip",
    "dismiss",
    name="swipe_direction",
    native_enum=False,
)
moderation_result_status = sa.Enum(
    "queued",
    "approved",
    "needs_review",
    "rejected",
    name="moderation_result_status",
    native_enum=False,
)
support_ticket_type = sa.Enum(
    "appeal",
    "bug_report",
    "improvement",
    name="support_ticket_type",
    native_enum=False,
)
support_ticket_status = sa.Enum(
    "open",
    "under_review",
    "waiting_for_user",
    "resolved",
    "closed",
    name="support_ticket_status",
    native_enum=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    issue_status.create(bind, checkfirst=True)
    moderation_state.create(bind, checkfirst=True)
    swipe_direction.create(bind, checkfirst=True)
    moderation_result_status.create(bind, checkfirst=True)
    support_ticket_type.create(bind, checkfirst=True)
    support_ticket_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("preferred_locale", sa.String(length=12), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_role_is_active", "users", ["role", "is_active"], unique=False)

    op.create_table(
        "issue_categories",
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        "ix_issue_categories_slug_is_active",
        "issue_categories",
        ["slug", "is_active"],
        unique=False,
    )

    op.create_table(
        "issues",
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("short_description", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("status", issue_status, nullable=False),
        sa.Column("moderation_state", moderation_state, nullable=False),
        sa.Column("source_locale", sa.String(length=12), nullable=False),
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
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["issue_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_issues_author_id", "issues", ["author_id"], unique=False)
    op.create_index("ix_issues_category_id", "issues", ["category_id"], unique=False)
    op.create_index(
        "ix_issues_author_created_at",
        "issues",
        ["author_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_issues_status_created_at",
        "issues",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_issues_category_created_at",
        "issues",
        ["category_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "issue_attachments",
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("uploader_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
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
        sa.ForeignKeyConstraint(["uploader_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        "ix_issue_attachments_issue_created_at",
        "issue_attachments",
        ["issue_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "swipe_feedback",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("direction", swipe_direction, nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "issue_id", name="uq_swipe_feedback_user_issue"),
    )
    op.create_index(
        "ix_swipe_feedback_issue_created_at",
        "swipe_feedback",
        ["issue_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "moderation_results",
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("status", moderation_result_status, nullable=False),
        sa.Column("provider_name", sa.String(length=120), nullable=True),
        sa.Column("model_name", sa.String(length=120), nullable=True),
        sa.Column("flags", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
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
    )
    op.create_index(
        "ix_moderation_results_issue_created_at",
        "moderation_results",
        ["issue_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_moderation_results_status_created_at",
        "moderation_results",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "support_tickets",
        sa.Column("issue_id", sa.Uuid(), nullable=True),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("ticket_type", support_ticket_type, nullable=False),
        sa.Column("status", support_ticket_status, nullable=False),
        sa.Column("subject", sa.String(length=160), nullable=False),
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
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_support_tickets_author_created_at",
        "support_tickets",
        ["author_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_support_tickets_status_created_at",
        "support_tickets",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "ticket_messages",
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False),
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
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ticket_messages_ticket_created_at",
        "ticket_messages",
        ["ticket_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "admin_action_logs",
        sa.Column("admin_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
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
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_action_logs_admin_created_at",
        "admin_action_logs",
        ["admin_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_action_logs_entity_type_entity_id",
        "admin_action_logs",
        ["entity_type", "entity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_admin_action_logs_entity_type_entity_id", table_name="admin_action_logs")
    op.drop_index("ix_admin_action_logs_admin_created_at", table_name="admin_action_logs")
    op.drop_table("admin_action_logs")

    op.drop_index("ix_ticket_messages_ticket_created_at", table_name="ticket_messages")
    op.drop_table("ticket_messages")

    op.drop_index("ix_support_tickets_status_created_at", table_name="support_tickets")
    op.drop_index("ix_support_tickets_author_created_at", table_name="support_tickets")
    op.drop_table("support_tickets")

    op.drop_index("ix_moderation_results_status_created_at", table_name="moderation_results")
    op.drop_index("ix_moderation_results_issue_created_at", table_name="moderation_results")
    op.drop_table("moderation_results")

    op.drop_index("ix_swipe_feedback_issue_created_at", table_name="swipe_feedback")
    op.drop_table("swipe_feedback")

    op.drop_index("ix_issue_attachments_issue_created_at", table_name="issue_attachments")
    op.drop_table("issue_attachments")

    op.drop_index("ix_issues_category_created_at", table_name="issues")
    op.drop_index("ix_issues_status_created_at", table_name="issues")
    op.drop_index("ix_issues_author_created_at", table_name="issues")
    op.drop_index("ix_issues_category_id", table_name="issues")
    op.drop_index("ix_issues_author_id", table_name="issues")
    op.drop_table("issues")

    op.drop_index("ix_issue_categories_slug_is_active", table_name="issue_categories")
    op.drop_table("issue_categories")

    op.drop_index("ix_users_role_is_active", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    support_ticket_status.drop(bind, checkfirst=True)
    support_ticket_type.drop(bind, checkfirst=True)
    moderation_result_status.drop(bind, checkfirst=True)
    swipe_direction.drop(bind, checkfirst=True)
    moderation_state.drop(bind, checkfirst=True)
    issue_status.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)
