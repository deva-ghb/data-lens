"""Learning cards, toolbox talks and SWP changes, and who has read them."""

import enum
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class LearningKind(enum.StrEnum):
    CARD = "card"
    TOOLBOX_TALK = "toolbox_talk"
    SWP_CHANGE = "swp_change"


class LearningStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    RETIRED = "retired"


class LearningItem(Base):
    __tablename__ = "learning_items"
    __table_args__ = (Index(None, "source_kind", "source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[LearningKind]
    # The record the lesson comes from; not a foreign key because it can be several tables.
    source_kind: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[int]
    draft_id: Mapped[int | None] = mapped_column(ForeignKey("ai_drafts.id"), index=True)
    status: Mapped[LearningStatus] = mapped_column(default=LearningStatus.DRAFT)


class LearningRead(Base):
    __tablename__ = "learning_reads"

    item_id: Mapped[int] = mapped_column(ForeignKey("learning_items.id"), primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"), primary_key=True, index=True)
    at: Mapped[datetime]
