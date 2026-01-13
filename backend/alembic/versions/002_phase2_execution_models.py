"""Phase 2: Execution Tracking Models

TAG: [SPEC-005] [DATABASE] [MIGRATION] [EXECUTION] [TRACKING]
REQ: REQ-001 - WorkflowExecution Model Definition
REQ: REQ-002 - NodeExecution Model Definition
REQ: REQ-003 - ExecutionLog Model Definition
REQ: REQ-004 - Workflow-WorkflowExecution Relationship
REQ: REQ-005 - WorkflowExecution-NodeExecution Relationship (CASCADE)
REQ: REQ-006 - WorkflowExecution-ExecutionLog Relationship (CASCADE)
REQ: REQ-007 - NodeExecution-ExecutionLog Relationship (CASCADE)
REQ: REQ-008 - State Transition Helpers
REQ: REQ-009 - Duration Properties

Creates tables for execution tracking:
- workflow_executions: Track workflow run instances
- node_executions: Track individual node executions
- execution_logs: Store execution log entries

Revision ID: 002_phase2
Revises: 001_phase1
Create Date: 2026-01-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_phase2"
down_revision: str | None = "001_phase1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create Phase 2 tables for execution tracking."""

    # ============================================================================
    # Create ENUM types
    # ============================================================================

    # Create executionstatus enum
    executionstatus_enum = postgresql.ENUM(
        "pending",
        "running",
        "completed",
        "failed",
        "skipped",
        "cancelled",
        name="executionstatus",
        create_type=False,  # Avoid conflicts if type already exists
    )
    executionstatus_enum.create(op.get_bind(), checkfirst=True)

    # Create triggertype enum (may already exist, use checkfirst)
    triggertype_enum = postgresql.ENUM(
        "schedule",
        "event",
        "manual",
        name="triggertype",
        create_type=False,
    )
    triggertype_enum.create(op.get_bind(), checkfirst=True)

    # Create loglevel enum
    loglevel_enum = postgresql.ENUM(
        "debug",
        "info",
        "warning",
        "error",
        name="loglevel",
        create_type=False,
    )
    loglevel_enum.create(op.get_bind(), checkfirst=True)

    # ============================================================================
    # Create workflow_executions table
    # ============================================================================

    op.create_table(
        "workflow_executions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "workflow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "trigger_type",
            triggertype_enum,
            nullable=False,
        ),
        sa.Column(
            "status",
            executionstatus_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "ended_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "input_data",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "output_data",
            postgresql.JSONB,
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sa.Text,
            nullable=True,
        ),
        sa.Column(
            "context",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ============================================================================
    # Create node_executions table
    # ============================================================================

    op.create_table(
        "node_executions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "workflow_execution_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nodes.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            executionstatus_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "ended_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "input_data",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "output_data",
            postgresql.JSONB,
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sa.Text,
            nullable=True,
        ),
        sa.Column(
            "error_traceback",
            sa.Text,
            nullable=True,
        ),
        sa.Column(
            "retry_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "execution_order",
            sa.Integer,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ============================================================================
    # Create execution_logs table
    # ============================================================================

    op.create_table(
        "execution_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "workflow_execution_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "node_execution_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("node_executions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "level",
            loglevel_enum,
            nullable=False,
        ),
        sa.Column(
            "message",
            sa.Text,
            nullable=False,
        ),
        sa.Column(
            "data",
            postgresql.JSONB,
            nullable=True,
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ============================================================================
    # Create indexes
    # ============================================================================

    # workflow_executions indexes (6 indexes)
    op.create_index(
        "idx_workflow_executions_workflow",
        "workflow_executions",
        ["workflow_id"],
    )
    op.create_index(
        "idx_workflow_executions_status",
        "workflow_executions",
        ["status"],
    )
    op.create_index(
        "idx_workflow_executions_trigger_type",
        "workflow_executions",
        ["trigger_type"],
    )
    op.create_index(
        "idx_workflow_executions_created_at",
        "workflow_executions",
        ["created_at"],
    )
    op.create_index(
        "idx_workflow_executions_workflow_status",
        "workflow_executions",
        ["workflow_id", "status"],
    )
    op.create_index(
        "idx_workflow_executions_status_created",
        "workflow_executions",
        ["status", "created_at"],
    )

    # node_executions indexes (5 indexes)
    op.create_index(
        "idx_node_executions_workflow_execution",
        "node_executions",
        ["workflow_execution_id"],
    )
    op.create_index(
        "idx_node_executions_node",
        "node_executions",
        ["node_id"],
    )
    op.create_index(
        "idx_node_executions_status",
        "node_executions",
        ["status"],
    )
    op.create_index(
        "idx_node_executions_execution_order",
        "node_executions",
        ["execution_order"],
    )
    op.create_index(
        "idx_node_executions_workflow_execution_order",
        "node_executions",
        ["workflow_execution_id", "execution_order"],
    )

    # execution_logs indexes (3 indexes)
    op.create_index(
        "idx_execution_logs_workflow_execution",
        "execution_logs",
        ["workflow_execution_id"],
    )
    op.create_index(
        "idx_execution_logs_node_execution",
        "execution_logs",
        ["node_execution_id"],
    )
    op.create_index(
        "idx_execution_logs_level_timestamp",
        "execution_logs",
        ["level", "timestamp"],
    )

    # JSONB GIN indexes for flexible queries
    op.create_index(
        "idx_workflow_executions_input_data",
        "workflow_executions",
        ["input_data"],
        postgresql_using="gin",
        postgresql_ops={"input_data": "jsonb_path_ops"},
    )
    op.create_index(
        "idx_workflow_executions_output_data",
        "workflow_executions",
        ["output_data"],
        postgresql_using="gin",
        postgresql_ops={"output_data": "jsonb_path_ops"},
    )
    op.create_index(
        "idx_workflow_executions_context",
        "workflow_executions",
        ["context"],
        postgresql_using="gin",
        postgresql_ops={"context": "jsonb_path_ops"},
    )
    op.create_index(
        "idx_node_executions_input_data",
        "node_executions",
        ["input_data"],
        postgresql_using="gin",
        postgresql_ops={"input_data": "jsonb_path_ops"},
    )
    op.create_index(
        "idx_node_executions_output_data",
        "node_executions",
        ["output_data"],
        postgresql_using="gin",
        postgresql_ops={"output_data": "jsonb_path_ops"},
    )


def downgrade() -> None:
    """Drop Phase 2 tables."""

    # Drop JSONB GIN indexes
    op.drop_index("idx_node_executions_output_data", table_name="node_executions")
    op.drop_index("idx_node_executions_input_data", table_name="node_executions")
    op.drop_index("idx_workflow_executions_context", table_name="workflow_executions")
    op.drop_index(
        "idx_workflow_executions_output_data", table_name="workflow_executions"
    )
    op.drop_index(
        "idx_workflow_executions_input_data", table_name="workflow_executions"
    )

    # Drop execution_logs indexes
    op.drop_index("idx_execution_logs_level_timestamp", table_name="execution_logs")
    op.drop_index("idx_execution_logs_node_execution", table_name="execution_logs")
    op.drop_index("idx_execution_logs_workflow_execution", table_name="execution_logs")

    # Drop node_executions indexes
    op.drop_index(
        "idx_node_executions_workflow_execution_order", table_name="node_executions"
    )
    op.drop_index("idx_node_executions_execution_order", table_name="node_executions")
    op.drop_index("idx_node_executions_status", table_name="node_executions")
    op.drop_index("idx_node_executions_node", table_name="node_executions")
    op.drop_index(
        "idx_node_executions_workflow_execution", table_name="node_executions"
    )

    # Drop workflow_executions indexes
    op.drop_index(
        "idx_workflow_executions_status_created", table_name="workflow_executions"
    )
    op.drop_index(
        "idx_workflow_executions_workflow_status", table_name="workflow_executions"
    )
    op.drop_index(
        "idx_workflow_executions_created_at", table_name="workflow_executions"
    )
    op.drop_index(
        "idx_workflow_executions_trigger_type", table_name="workflow_executions"
    )
    op.drop_index("idx_workflow_executions_status", table_name="workflow_executions")
    op.drop_index("idx_workflow_executions_workflow", table_name="workflow_executions")

    # Drop tables in reverse order (respecting FK dependencies)
    op.drop_table("execution_logs")
    op.drop_table("node_executions")
    op.drop_table("workflow_executions")

    # Drop enums
    sa.Enum(name="loglevel").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="triggertype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="executionstatus").drop(op.get_bind(), checkfirst=True)
