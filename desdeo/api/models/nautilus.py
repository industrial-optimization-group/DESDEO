import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String

from desdeo.api.db import Base


class NautilusStateDB(Base):
    """Database model storing the state of a NAUTILUS interactive navigation session.

    Each record represents a single interaction step within a NAUTILUS session,
    such as initialization, navigation, or finalization. The table supports
    branching session trees by maintaining parent-child relationships between states.

    Attributes:
        id (int): Primary key identifying this state entry.
        session_id (int): Identifier of the interactive NAUTILUS session.
        parent_state_id (int | None): Foreign key referencing the parent state.
            Null for root (initialization) nodes.
        request (JSON): Serialized Nautilus request model used to generate this state.
        response (JSON): Serialized Nautilus response model produced by the algorithm.
        node_type (str): Type of interaction that generated the state.
            Expected values include:
                - "initialize"
                - "navigate"
                - "final"
        depth (int): Depth of this node within the session tree (root = 0).
        created_at (datetime): Timestamp when this state was created.
    """

    __tablename__ = "nautilus_states"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, nullable=False)
    parent_state_id = Column(Integer, ForeignKey("nautilus_states.id"), nullable=True)

    request = Column(JSON, nullable=False)
    response = Column(JSON, nullable=False)

    node_type = Column(String, nullable=False)  # "initialize", "navigate", "final"

    depth = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
