"""
models/subscription.py
----------------------
Subscription/trial lifecycle state separate from paid policy records.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from db.connection import Base


class SubscriptionState(Base):
    """
    Tracks a rider's trial lifecycle, dynamic premium quotes, and notification
    state without overloading paid policy rows.
    """

    __tablename__ = "subscription_states"

    id = Column(Integer, Identity(always=True), primary_key=True)
    rider_id = Column(
        Integer,
        ForeignKey("riders.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    phase = Column(String(20), nullable=False, default="trial_active")
    trial_started_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    trial_completed_at = Column(DateTime(timezone=True), nullable=True)
    last_seeded_at = Column(DateTime(timezone=True), nullable=True)
    last_quotes_at = Column(DateTime(timezone=True), nullable=True)
    premium_quotes = Column(JSONB, nullable=False, default=dict)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
    notification_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=text("NOW()"), onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "phase IN ('trial_active', 'plan_selection', 'paid_active')",
            name="ck_subscription_states_phase",
        ),
    )

    rider = relationship("Rider", back_populates="subscription_state")

    def to_dict(self):
        return {
            "id": self.id,
            "rider_id": self.rider_id,
            "phase": self.phase,
            "trial_started_at": self.trial_started_at.isoformat() if self.trial_started_at else None,
            "trial_completed_at": self.trial_completed_at.isoformat() if self.trial_completed_at else None,
            "last_seeded_at": self.last_seeded_at.isoformat() if self.last_seeded_at else None,
            "last_quotes_at": self.last_quotes_at.isoformat() if self.last_quotes_at else None,
            "premium_quotes": self.premium_quotes or {},
            "last_notified_at": self.last_notified_at.isoformat() if self.last_notified_at else None,
            "notification_seen_at": self.notification_seen_at.isoformat() if self.notification_seen_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
