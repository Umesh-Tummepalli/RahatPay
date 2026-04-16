"""
models/policy.py  (Module 3 — Triggers & Claims)
-------------------------------------------------
Read/write ORM models for policies, claims, disruption_events, payouts.
Module 1 owns the schema; Module 3 writes claims and payouts.
Imports Base from Module 3's own db.connection (NOT Module 1's).
"""

from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, Date,
    ForeignKey, CheckConstraint, Text, text, Identity
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from db.connection import Base


class Policy(Base):
    """Insurance policy locked for a 4-week cycle."""
    __tablename__ = "policies"

    id                = Column(Integer, Identity(always=True), primary_key=True)
    rider_id          = Column(Integer, ForeignKey("riders.id", ondelete="RESTRICT"), nullable=False, index=True)
    tier              = Column(String(20), nullable=False)
    weekly_premium    = Column(Numeric(10, 2), nullable=False)
    premium_breakdown = Column(JSONB, nullable=False, default=dict)
    weekly_payout_cap = Column(Numeric(10, 2), nullable=False)
    coverage_type     = Column(String(100), nullable=False)
    status            = Column(String(20), nullable=False, default="active")
    cycle_start_date  = Column(Date, nullable=False)
    cycle_end_date    = Column(Date, nullable=False, index=True)
    created_at        = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at        = Column(DateTime(timezone=True), server_default=text("NOW()"), onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("tier IN ('kavach', 'suraksha', 'raksha')", name="ck_policies_tier"),
        CheckConstraint("weekly_premium >= 15", name="ck_policies_premium_floor"),
        CheckConstraint("weekly_payout_cap > 0", name="ck_policies_payout_cap"),
        CheckConstraint("status IN ('active', 'expired', 'cancelled', 'pending')", name="ck_policies_status"),
        CheckConstraint("cycle_end_date > cycle_start_date", name="ck_policies_dates_order"),
        CheckConstraint("cycle_end_date = cycle_start_date + INTERVAL '28 days'", name="ck_policies_4week_cycle"),
    )

    rider  = relationship("Rider", back_populates="policies")
    claims = relationship("Claim", back_populates="policy")

    @property
    def is_active(self) -> bool:
        return self.status == "active" and self.cycle_end_date >= date.today()

    @property
    def days_remaining(self) -> int:
        if self.cycle_end_date:
            delta = self.cycle_end_date - date.today()
            return max(0, delta.days)
        return 0

    def to_dict(self):
        return {
            "id":               self.id,
            "rider_id":         self.rider_id,
            "tier":             self.tier,
            "weekly_premium":   float(self.weekly_premium),
            "premium_breakdown": self.premium_breakdown,
            "weekly_payout_cap": float(self.weekly_payout_cap),
            "coverage_type":    self.coverage_type,
            "status":           self.status,
            "cycle_start_date": self.cycle_start_date.isoformat() if self.cycle_start_date else None,
            "cycle_end_date":   self.cycle_end_date.isoformat() if self.cycle_end_date else None,
            "days_remaining":   self.days_remaining,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
            "updated_at":       self.updated_at.isoformat() if self.updated_at else None,
        }


class DisruptionEvent(Base):
    """Weather / civic disruption events created by Module 3's trigger poller."""
    __tablename__ = "disruption_events"

    id                = Column(Integer, Identity(always=True), primary_key=True)
    event_type        = Column(String(50), nullable=False)
    severity          = Column(String(20), nullable=False)
    payout_rate       = Column(Numeric(5, 4), nullable=False)
    affected_zone     = Column(Integer, ForeignKey("zones.zone_id"), nullable=False, index=True)
    trigger_data      = Column(JSONB, nullable=False, default=dict)
    event_start       = Column(DateTime(timezone=True), nullable=False, index=True)
    event_end         = Column(DateTime(timezone=True), nullable=True)
    processing_status = Column(String(20), nullable=False, default="pending")
    created_at        = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at        = Column(DateTime(timezone=True), server_default=text("NOW()"), onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('heavy_rain','cyclone','flood','extreme_heat','poor_aqi','civic_disruption','storm','other')",
            name="ck_disruption_event_type"
        ),
        CheckConstraint(
            "severity IN ('moderate','severe_l1','severe_l2','extreme')",
            name="ck_disruption_severity"
        ),
        CheckConstraint("payout_rate BETWEEN 0 AND 1", name="ck_disruption_payout_rate"),
        CheckConstraint(
            "processing_status IN ('pending','processing','processed','failed')",
            name="ck_disruption_processing_status"
        ),
    )

    claims = relationship("Claim", back_populates="disruption_event")


class Claim(Base):
    """Insurance claim generated per rider per disruption event."""
    __tablename__ = "claims"

    id                  = Column(Integer, Identity(always=True), primary_key=True)
    rider_id            = Column(Integer, ForeignKey("riders.id", ondelete="RESTRICT"), nullable=False, index=True)
    policy_id           = Column(Integer, ForeignKey("policies.id", ondelete="RESTRICT"), nullable=False, index=True)
    disruption_event_id = Column(Integer, ForeignKey("disruption_events.id"), nullable=False, index=True)
    gate_results        = Column(JSONB, nullable=False, default=dict)
    is_eligible         = Column(Boolean, nullable=False, default=False)
    ineligibility_reason = Column(Text, nullable=True)
    lost_hours          = Column(Numeric(6, 2), nullable=True)
    hourly_rate         = Column(Numeric(10, 2), nullable=True)
    severity_rate       = Column(Numeric(5, 4), nullable=True)
    calculated_payout   = Column(Numeric(10, 2), nullable=True)
    final_payout        = Column(Numeric(10, 2), nullable=True)
    status              = Column(String(20), nullable=False, default="pending", index=True)
    created_at          = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at          = Column(DateTime(timezone=True), server_default=text("NOW()"), onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "final_payout IS NULL OR (final_payout >= 0 AND final_payout <= 5000)",
            name="ck_claims_final_payout_cap"
        ),
        CheckConstraint(
            "status IN ('pending','approved','rejected','paid','failed')",
            name="ck_claims_status"
        ),
        CheckConstraint("lost_hours IS NULL OR lost_hours >= 0", name="ck_claims_lost_hours"),
    )

    rider            = relationship("Rider", back_populates="claims")
    policy           = relationship("Policy", back_populates="claims")
    disruption_event = relationship("DisruptionEvent", back_populates="claims")
    payouts          = relationship("Payout", back_populates="claim")

    def to_dict(self):
        return {
            "id":                   self.id,
            "rider_id":             self.rider_id,
            "policy_id":            self.policy_id,
            "disruption_event_id":  self.disruption_event_id,
            "gate_results":         self.gate_results,
            "is_eligible":          self.is_eligible,
            "ineligibility_reason": self.ineligibility_reason,
            "lost_hours":           float(self.lost_hours) if self.lost_hours else None,
            "hourly_rate":          float(self.hourly_rate) if self.hourly_rate else None,
            "severity_rate":        float(self.severity_rate) if self.severity_rate else None,
            "calculated_payout":    float(self.calculated_payout) if self.calculated_payout else None,
            "final_payout":         float(self.final_payout) if self.final_payout else None,
            "status":               self.status,
            "created_at":           self.created_at.isoformat() if self.created_at else None,
            "updated_at":           self.updated_at.isoformat() if self.updated_at else None,
        }


class Payout(Base):
    """Disbursement record per claim. Module 3 creates payouts."""
    __tablename__ = "payouts"

    id                = Column(Integer, Identity(always=True), primary_key=True)
    claim_id          = Column(Integer, ForeignKey("claims.id", ondelete="RESTRICT"), nullable=False, index=True)
    rider_id          = Column(Integer, ForeignKey("riders.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount            = Column(Numeric(10, 2), nullable=False)
    gateway           = Column(String(50), nullable=False, default="razorpay")
    gateway_reference = Column(String(200), nullable=True)
    gateway_response  = Column(JSONB, nullable=False, default=dict)
    upi_id            = Column(String(200), nullable=True)
    status            = Column(String(20), nullable=False, default="initiated", index=True)
    initiated_at      = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    completed_at      = Column(DateTime(timezone=True), nullable=True)
    created_at        = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at        = Column(DateTime(timezone=True), server_default=text("NOW()"), onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("amount > 0 AND amount <= 5000", name="ck_payouts_amount"),
        CheckConstraint("gateway IN ('razorpay','manual','test')", name="ck_payouts_gateway"),
        CheckConstraint(
            "status IN ('initiated','processing','success','failed','reversed')",
            name="ck_payouts_status"
        ),
    )

    claim  = relationship("Claim", back_populates="payouts")
    rider  = relationship("Rider", back_populates="payouts")

    def to_dict(self):
        return {
            "id":                self.id,
            "claim_id":          self.claim_id,
            "rider_id":          self.rider_id,
            "amount":            float(self.amount),
            "gateway":           self.gateway,
            "gateway_reference": self.gateway_reference,
            "status":            self.status,
            "initiated_at":      self.initiated_at.isoformat() if self.initiated_at else None,
            "completed_at":      self.completed_at.isoformat() if self.completed_at else None,
            "created_at":        self.created_at.isoformat() if self.created_at else None,
            "updated_at":        self.updated_at.isoformat() if self.updated_at else None,
        }
