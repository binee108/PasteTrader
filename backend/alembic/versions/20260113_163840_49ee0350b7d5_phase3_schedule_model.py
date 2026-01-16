"""Add Schedule model and relationships.

Revision ID: 49ee0350b7d5
Revises: 002_phase2_execution_models
Create Date: 2026-01-13 16:38:40

TAG: [SPEC-006] [DATABASE] [MIGRATION]
REQ: REQ-001 - Schedule Model Definition
REQ: REQ-002 - ScheduleType Enum Definition
REQ: REQ-004 - Workflow-Schedule Relationship
REQ: REQ-005 - User-Schedule Relationship
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "49ee0350b7d5"
down_revision: str | None = "002_phase2_execution_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade database schema - Add schedules table."""
    # Create schedules table
    op.create_table(
        "schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("schedule_type", sa.String(length=50), nullable=False),
        sa.Column("schedule_config", sa.JSON(), nullable=False),
        sa.Column(
            "timezone", sa.String(length=50), nullable=False, server_default="UTC"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("job_id", sa.String(length=255), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["workflows.id"],
            name="fk_schedules_workflow_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_schedules_user_id", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_schedules"),
        sa.UniqueConstraint("job_id", name="uq_schedules_job_id"),
    )

    # Create indexes for schedules table
    op.create_index("ix_schedules_workflow_id", "schedules", ["workflow_id"])
    op.create_index("ix_schedules_user_id", "schedules", ["user_id"])
    op.create_index("ix_schedules_schedule_type", "schedules", ["schedule_type"])
    op.create_index("ix_schedules_job_id", "schedules", ["job_id"], unique=True)
    op.create_index("ix_schedules_next_run_at", "schedules", ["next_run_at"])

    # Create composite index for workflow and active status
    op.create_index(
        "ix_schedules_workflow_active", "schedules", ["workflow_id", "is_active"]
    )


def downgrade() -> None:
    """Downgrade database schema - Remove schedules table."""
    # Drop schedules table
    op.drop_table("schedules")
