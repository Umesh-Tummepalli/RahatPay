"""
models/rider.py
---------------
SQLAlchemy ORM model for the `riders` table.
Also includes the `zones` table model since zones are part of rider identity.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime,
    ForeignKey, CheckConstraint, text, Identity
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from db.connection import Base


class Zone(Base):
    """
    Reference table for delivery zones.
    Populated once; Module 1 owns it, all modules read it.
    """
    __tablename__ = "zones"

    zone_id         = Column(Integer, Identity(always=True), primary_key=True)
    city            = Column(String(100), nullable=False)
    area_name       = Column(String(200), nullable=False)
    
    # Polygon stored as JSONB; can be migrated to PostGIS in production.
    # Validation occurs at application level for min 3 points and valid lat/lng.
    polygon         = Column(JSONB, nullable=False, default=list)
    risk_multiplier = Column(Numeric(4, 2), nullable=False)
    is_active       = Column(Boolean, nullable=False, default=True)
    registration_cap = Column(Integer, nullable=False, default=1000)
    created_at      = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "risk_multiplier BETWEEN 0.80 AND 1.50",
            name="ck_zones_risk_range"
        ),
    )

    # Back-references
    riders_zone1    = relationship("Rider", foreign_keys="Rider.zone1_id", back_populates="zone1")
    riders_zone2    = relationship("Rider", foreign_keys="Rider.zone2_id", back_populates="zone2")
    riders_zone3    = relationship("Rider", foreign_keys="Rider.zone3_id", back_populates="zone3")

    def to_dict(self):
        return {
            "zone_id":          self.zone_id,
            "city":             self.city,
            "area_name":        self.area_name,
            "polygon":          self.polygon,
            "risk_multiplier":  float(self.risk_multiplier),
            "is_active":        self.is_active,
            "registration_cap": self.registration_cap,
        }


class Rider(Base):
    """
    Core identity table. Single source of truth for rider data.
    All other modules reference this via rider_id.
    """
    __tablename__ = "riders"

    id                      = Column(Integer, Identity(always=True), primary_key=True)
    partner_id              = Column(String(100), nullable=False, unique=True, index=True)
    platform                = Column(String(20), nullable=False)
    name                    = Column(String(200), nullable=False)
    phone                   = Column(String(15), nullable=False, unique=True, index=True)
    aadhaar_last4           = Column(String(4), nullable=True)
    pan                     = Column(String(10), nullable=True)
    city                    = Column(String(100), nullable=False, index=True)
    
    # Future improvement: normalize into rider_zones table.
    zone1_id                = Column(Integer, ForeignKey("zones.zone_id"), nullable=False, index=True)
    zone2_id                = Column(Integer, ForeignKey("zones.zone_id"), nullable=True)
    zone3_id                = Column(Integer, ForeignKey("zones.zone_id"), nullable=True)
    
    tier                    = Column(String(20), nullable=False)
    baseline_weekly_income  = Column(Numeric(10, 2), nullable=True)
    baseline_weekly_hours   = Column(Numeric(6, 2), nullable=True)
    daily_income_history    = Column(JSONB, nullable=True, default=list)
    is_seasoning            = Column(Boolean, nullable=False, default=True)
    trust_score             = Column(Numeric(5, 2), nullable=False, default=50.00)
    
    # Admin fields
    is_blocked              = Column(Boolean, nullable=False, default=False)
    kyc_verified            = Column(Boolean, nullable=False, default=False)
    
    created_at              = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at              = Column(DateTime(timezone=True), server_default=text("NOW()"), onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "platform IN ('swiggy', 'zomato', 'dunzo', 'other')",
            name="ck_riders_platform"
        ),
        CheckConstraint(
            "tier IN ('kavach', 'suraksha', 'raksha')",
            name="ck_riders_tier"
        ),
        CheckConstraint(
            "aadhaar_last4 IS NOT NULL OR pan IS NOT NULL",
            name="ck_riders_kyc_required"
        ),
        CheckConstraint(
            "trust_score BETWEEN 0 AND 100",
            name="ck_riders_trust_score"
        ),
        CheckConstraint(
            "baseline_weekly_income IS NULL OR baseline_weekly_income >= 0",
            name="ck_riders_income_positive"
        ),
    )

    # Relationships
    zone1       = relationship("Zone", foreign_keys=[zone1_id], back_populates="riders_zone1")
    zone2       = relationship("Zone", foreign_keys=[zone2_id], back_populates="riders_zone2")
    zone3       = relationship("Zone", foreign_keys=[zone3_id], back_populates="riders_zone3")
    policies    = relationship("Policy", back_populates="rider", cascade="all, delete-orphan")
    claims      = relationship("Claim", back_populates="rider")
    payouts     = relationship("Payout", back_populates="rider")
    subscription_state = relationship(
        "SubscriptionState",
        back_populates="rider",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def active_policy(self):
        """Returns the current active policy, if any."""
        from datetime import date
        for p in self.policies:
            if p.status == "active" and p.cycle_end_date >= date.today():
                return p
        return None

    @property
    def baseline_hourly_rate(self) -> float | None:
        """Derived: income / hours."""
        if self.baseline_weekly_income and self.baseline_weekly_hours and self.baseline_weekly_hours > 0:
            return float(self.baseline_weekly_income) / float(self.baseline_weekly_hours)
        return None

    def to_dict(self):
        kyc_doc_types = []
        if self.aadhaar_last4:
            kyc_doc_types.append("Aadhaar")
        if self.pan:
            kyc_doc_types.append("PAN")

        return {
            "id":                       self.id,
            "partner_id":               self.partner_id,
            "platform":                 self.platform,
            "name":                     self.name,
            "phone":                    self.phone,
            "aadhaar_last4":            self.aadhaar_last4,
            "pan_masked":               f"{self.pan[:5]}****{self.pan[-1]}" if self.pan else None,
            "kyc_document_type":        " + ".join(kyc_doc_types) if kyc_doc_types else "Unknown",
            "city":                     self.city,
            "tier":                     self.tier,
            "zone1_id":                 self.zone1_id,
            "zone2_id":                 self.zone2_id,
            "zone3_id":                 self.zone3_id,
            "baseline_weekly_income":   float(self.baseline_weekly_income) if self.baseline_weekly_income else None,
            "baseline_weekly_hours":    float(self.baseline_weekly_hours) if self.baseline_weekly_hours else None,
            "daily_income_history":     self.daily_income_history if hasattr(self, 'daily_income_history') and self.daily_income_history is not None else [],
            "baseline_hourly_rate":     self.baseline_hourly_rate,
            "is_seasoning":             self.is_seasoning,
            "trust_score":              float(self.trust_score),
            "is_blocked":               self.is_blocked,
            "kyc_verified":             self.kyc_verified,
            "created_at":               self.created_at.isoformat() if self.created_at else None,
            "updated_at":               self.updated_at.isoformat() if getattr(self, "updated_at", None) else None,
        }
