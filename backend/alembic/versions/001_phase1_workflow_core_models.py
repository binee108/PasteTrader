"""Phase 1: Workflow Core Models

TAG: [SPEC-003] [SPEC-004] [DATABASE] [MIGRATION]
REQ: Phase 1 - Workflow Core Models

Creates tables for:
- tools: External tool registry (SPEC-004)
- agents: LLM agent configuration (SPEC-004)
- workflows: DAG workflow definitions (SPEC-003)
- nodes: Workflow nodes with 6 types (SPEC-003)
- edges: Node connections (SPEC-003)

Revision ID: 001_phase1
Revises: None
Create Date: 2026-01-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_phase1"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create Phase 1 tables."""
    # Create node_type enum
    node_type_enum = postgresql.ENUM(
        "trigger",
        "tool",
        "agent",
        "condition",
        "adapter",
        "parallel",
        "aggregator",
        name="nodetype",
        create_type=False,
    )
    node_type_enum.create(op.get_bind(), checkfirst=True)

    # Create tool_type enum
    tool_type_enum = postgresql.ENUM(
        "http",
        "mcp",
        "python",
        "shell",
        "builtin",
        name="tooltype",
        create_type=False,
    )
    tool_type_enum.create(op.get_bind(), checkfirst=True)

    # Create model_provider enum
    model_provider_enum = postgresql.ENUM(
        "anthropic",
        "openai",
        "glm",
        name="modelprovider",
        create_type=False,
    )
    model_provider_enum.create(op.get_bind(), checkfirst=True)

    # Create tools table (SPEC-004)
    op.create_table(
        "tools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "tool_type",
            tool_type_enum,
            nullable=False,
        ),
        sa.Column(
            "config",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "input_schema",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column("output_schema", postgresql.JSONB, nullable=True),
        sa.Column("auth_config", postgresql.JSONB, nullable=True),
        sa.Column("rate_limit", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="false"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create agents table (SPEC-004)
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "model_provider",
            model_provider_enum,
            nullable=False,
        ),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("system_prompt", sa.Text, nullable=True),
        sa.Column(
            "config",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "tools",
            postgresql.JSONB,
            nullable=False,
            server_default="[]",
        ),
        sa.Column("memory_config", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="false"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create workflows table (SPEC-003)
    op.create_table(
        "workflows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "config",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "variables",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create nodes table (SPEC-003)
    op.create_table(
        "nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "node_type",
            node_type_enum,
            nullable=False,
        ),
        sa.Column("position_x", sa.Float, nullable=False, server_default="0"),
        sa.Column("position_y", sa.Float, nullable=False, server_default="0"),
        sa.Column(
            "config",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column("input_schema", postgresql.JSONB, nullable=True),
        sa.Column("output_schema", postgresql.JSONB, nullable=True),
        sa.Column(
            "tool_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tools.id"),
            nullable=True,
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id"),
            nullable=True,
        ),
        sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default="300"),
        sa.Column(
            "retry_config",
            postgresql.JSONB,
            nullable=False,
            server_default='{"max_retries": 3, "delay": 1}',
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

    # Create edges table (SPEC-003)
    op.create_table(
        "edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_handle", sa.String(50), nullable=True),
        sa.Column("target_handle", sa.String(50), nullable=True),
        sa.Column("condition", postgresql.JSONB, nullable=True),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Unique constraint for edge connections
        sa.UniqueConstraint(
            "source_node_id",
            "target_node_id",
            "source_handle",
            "target_handle",
            name="uq_edge_connection",
        ),
        # Check constraint to prevent self-loops
        sa.CheckConstraint(
            "source_node_id != target_node_id",
            name="ck_no_self_loop",
        ),
    )

    # Create indexes
    # Tools indexes
    op.create_index(
        "idx_tools_owner",
        "tools",
        ["owner_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Agents indexes
    op.create_index(
        "idx_agents_owner",
        "agents",
        ["owner_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Workflows indexes
    op.create_index(
        "idx_workflows_owner",
        "workflows",
        ["owner_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "idx_workflows_owner_active",
        "workflows",
        ["owner_id", "is_active"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Nodes indexes
    op.create_index("idx_nodes_workflow", "nodes", ["workflow_id"])
    op.create_index("idx_nodes_type", "nodes", ["workflow_id", "node_type"])

    # Edges indexes
    op.create_index("idx_edges_workflow", "edges", ["workflow_id"])
    op.create_index("idx_edges_source", "edges", ["source_node_id"])
    op.create_index("idx_edges_target", "edges", ["target_node_id"])

    # JSONB GIN indexes for flexible queries
    op.create_index(
        "idx_tools_config",
        "tools",
        ["config"],
        postgresql_using="gin",
        postgresql_ops={"config": "jsonb_path_ops"},
    )
    op.create_index(
        "idx_agents_config",
        "agents",
        ["config"],
        postgresql_using="gin",
        postgresql_ops={"config": "jsonb_path_ops"},
    )
    op.create_index(
        "idx_workflows_config",
        "workflows",
        ["config"],
        postgresql_using="gin",
        postgresql_ops={"config": "jsonb_path_ops"},
    )
    op.create_index(
        "idx_nodes_config",
        "nodes",
        ["config"],
        postgresql_using="gin",
        postgresql_ops={"config": "jsonb_path_ops"},
    )


def downgrade() -> None:
    """Drop Phase 1 tables."""
    # Drop indexes
    op.drop_index("idx_nodes_config", table_name="nodes")
    op.drop_index("idx_workflows_config", table_name="workflows")
    op.drop_index("idx_agents_config", table_name="agents")
    op.drop_index("idx_tools_config", table_name="tools")

    op.drop_index("idx_edges_target", table_name="edges")
    op.drop_index("idx_edges_source", table_name="edges")
    op.drop_index("idx_edges_workflow", table_name="edges")

    op.drop_index("idx_nodes_type", table_name="nodes")
    op.drop_index("idx_nodes_workflow", table_name="nodes")

    op.drop_index("idx_workflows_owner_active", table_name="workflows")
    op.drop_index("idx_workflows_owner", table_name="workflows")

    op.drop_index("idx_agents_owner", table_name="agents")
    op.drop_index("idx_tools_owner", table_name="tools")

    # Drop tables in reverse order (respecting FK dependencies)
    op.drop_table("edges")
    op.drop_table("nodes")
    op.drop_table("workflows")
    op.drop_table("agents")
    op.drop_table("tools")

    # Drop enums
    sa.Enum(name="modelprovider").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="tooltype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="nodetype").drop(op.get_bind(), checkfirst=True)
