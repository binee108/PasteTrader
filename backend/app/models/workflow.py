"""Workflow, Node, and Edge models for DAG-based workflow definitions.

TAG: [SPEC-003] [DATABASE] [WORKFLOW] [NODE] [EDGE]
REQ: REQ-001 - Workflow Model Definition
REQ: REQ-002 - Node Model Definition
REQ: REQ-003 - Edge Model Definition
REQ: REQ-004 - Workflow-Node Relationship (CASCADE)
REQ: REQ-005 - Node-Edge Relationship (CASCADE)
REQ: REQ-006 - Optimistic Locking Support
REQ: REQ-007 - Edge Uniqueness Constraint
REQ: REQ-009 - Self-Loop Prevention

This module defines the core workflow models for PasteTrader's DAG-based
workflow engine. These models support visual workflow editing and execution.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import NodeType

# Use JSONB for PostgreSQL, JSON for other databases (like SQLite for testing)
JSONType = JSON().with_variant(JSONB(), "postgresql")


class Workflow(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Workflow model for DAG-based workflow definitions.

    Represents a workflow container that holds nodes and edges.
    Supports optimistic locking via the version field.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        owner_id: UUID of the user who owns this workflow
        name: Display name of the workflow
        description: Optional description of the workflow's purpose
        config: JSONB configuration for global workflow settings
        variables: JSONB storage for workflow variables
        is_active: Whether the workflow is active and runnable
        version: Version number for optimistic locking
        created_at: Timestamp of creation (from TimestampMixin)
        updated_at: Timestamp of last update (from TimestampMixin)
        deleted_at: Soft delete timestamp (from SoftDeleteMixin)
        nodes: Relationship to Node models
        edges: Relationship to Edge models
    """

    __tablename__ = "workflows"

    # Foreign key to users table (string reference for forward compatibility)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Basic information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # JSON fields for flexible configuration
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    variables: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Status and versioning
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    # Relationships
    nodes: Mapped[list["Node"]] = relationship(
        "Node",
        back_populates="workflow",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    edges: Mapped[list["Edge"]] = relationship(
        "Edge",
        back_populates="workflow",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        """Return string representation of the workflow."""
        return f"<Workflow(id={self.id}, name='{self.name}', version={self.version})>"


class Node(UUIDMixin, TimestampMixin, Base):
    """Node model for workflow nodes.

    Represents a single node in a workflow DAG. Supports 6 node types:
    trigger, tool, agent, condition, adapter, and aggregator.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        workflow_id: UUID of the parent workflow
        name: Display name of the node
        node_type: Type of node (NodeType enum)
        position_x: X coordinate for UI positioning
        position_y: Y coordinate for UI positioning
        config: JSONB configuration for node-specific settings
        input_schema: JSON Schema for input validation
        output_schema: JSON Schema for output validation
        tool_id: UUID of linked tool (for tool nodes)
        agent_id: UUID of linked agent (for agent nodes)
        timeout_seconds: Execution timeout in seconds
        retry_config: JSONB retry configuration
        created_at: Timestamp of creation (from TimestampMixin)
        updated_at: Timestamp of last update (from TimestampMixin)
        workflow: Relationship to parent Workflow
    """

    __tablename__ = "nodes"

    # Foreign key to workflows table with CASCADE delete
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Basic information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Node type enum
    node_type: Mapped[NodeType] = mapped_column(
        String(50),
        nullable=False,
    )

    # UI positioning (float for precise positioning)
    position_x: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0.0",
    )

    position_y: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0.0",
    )

    # JSON fields for flexible configuration
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    input_schema: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )

    output_schema: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )

    # Foreign keys to tools and agents (nullable)
    tool_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tools.id"),
        nullable=True,
    )

    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agents.id"),
        nullable=True,
    )

    # Execution configuration
    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=300,
        server_default="300",
    )

    retry_config: Mapped[dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=lambda: {"max_retries": 3, "delay": 1},
        server_default='{"max_retries": 3, "delay": 1}',
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="nodes",
    )

    def __repr__(self) -> str:
        """Return string representation of the node."""
        return f"<Node(id={self.id}, name='{self.name}', type={self.node_type})>"


class Edge(UUIDMixin, Base):
    """Edge model for workflow connections.

    Represents a connection between two nodes in a workflow DAG.
    Supports conditional branching and multiple handles.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        workflow_id: UUID of the parent workflow
        source_node_id: UUID of the source node
        target_node_id: UUID of the target node
        source_handle: Handle identifier on source node (for multiple outputs)
        target_handle: Handle identifier on target node (for multiple inputs)
        condition: JSONB condition for conditional edges
        priority: Execution priority for multiple outgoing edges
        label: Display label for the edge
        created_at: Timestamp of creation
        workflow: Relationship to parent Workflow
        source_node: Relationship to source Node
        target_node: Relationship to target Node
    """

    __tablename__ = "edges"

    # Foreign key to workflows table with CASCADE delete
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Foreign keys to nodes with CASCADE delete
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    target_node_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Handle identifiers for multi-output/input nodes
    source_handle: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    target_handle: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Condition for conditional edges
    condition: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType,
        nullable=True,
    )

    # Execution priority
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    # Display label
    label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Only created_at for edges (no updated_at)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="edges",
    )

    source_node: Mapped["Node"] = relationship(
        "Node",
        foreign_keys=[source_node_id],
    )

    target_node: Mapped["Node"] = relationship(
        "Node",
        foreign_keys=[target_node_id],
    )

    # Table constraints
    __table_args__ = (
        # Unique constraint for edge connections
        UniqueConstraint(
            "source_node_id",
            "target_node_id",
            "source_handle",
            "target_handle",
            name="uq_edge_connection",
        ),
        # Check constraint to prevent self-loops
        CheckConstraint(
            "source_node_id != target_node_id",
            name="ck_no_self_loop",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of the edge."""
        return (
            f"<Edge(id={self.id}, "
            f"source={self.source_node_id}, "
            f"target={self.target_node_id})>"
        )


__all__ = ["Workflow", "Node", "Edge"]
