import uuid
from datetime import datetime, timezone
from sqlalchemy import Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db import Base


class PipelineState(Base):
    __tablename__ = "pipeline_states"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunities.id"), unique=True, nullable=False
    )
    # 0 = not started, 1-12 = current step, 13 = complete
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    # Stores step outputs as they complete: {1: {...}, 2: {...}, ...}
    step_outputs: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
