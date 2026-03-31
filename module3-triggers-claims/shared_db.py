from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Use SQLite for standalone testing. Person 1 will replace this with PostgreSQL.
SQLALCHEMY_DATABASE_URL = "sqlite:///./module3_test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Rider(Base):
    __tablename__ = "riders"
    
    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(String, unique=True, index=True)
    platform = Column(String)
    name = Column(String)
    phone = Column(String)
    city = Column(String)
    tier_choice = Column(String)
    zone1_pincode = Column(String)
    zone2_pincode = Column(String)
    zone3_pincode = Column(String)
    baseline_income = Column(Float)
    baseline_hours = Column(Float)
    is_seasoning = Column(Boolean, default=False)
    trust_score = Column(Float, default=100.0)

class Policy(Base):
    __tablename__ = "policies"
    
    id = Column(Integer, primary_key=True, index=True)
    rider_id = Column(Integer, index=True)
    tier = Column(String)
    weekly_premium = Column(Float)
    weekly_payout_cap = Column(Float)
    status = Column(String)

class DisruptionEvent(Base):
    __tablename__ = "disruption_events"
    
    id = Column(Integer, primary_key=True, index=True)
    zone = Column(String, index=True)
    type = Column(String) # rainfall, aqi, heat, civic
    severity_level = Column(String)
    severity_payout_rate = Column(Float)
    api_source = Column(String)
    raw_measurement = Column(Float)
    start_time = Column(DateTime, default=datetime.utcnow)
    duration_hours = Column(Float)
    is_active = Column(Boolean, default=True)

class Claim(Base):
    __tablename__ = "claims"
    
    id = Column(Integer, primary_key=True, index=True)
    rider_id = Column(Integer, index=True)
    disruption_event_id = Column(Integer, index=True)
    
    disrupted_hours = Column(Float)
    hourly_rate = Column(Float)
    disrupted_income = Column(Float)
    severity_rate = Column(Float)
    gross_payout = Column(Float)
    weekly_cap = Column(Float)
    already_paid = Column(Float)
    final_payout = Column(Float)
    
    # 4 gates
    gate1_zone_match = Column(Boolean)
    gate2_shift_overlap = Column(Boolean)
    gate3_platform_inactivity = Column(Boolean)
    gate4_sensor_fusion = Column(Boolean)
    
    rejection_reason = Column(String, nullable=True)
    status = Column(String, default="pending") # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)

class Payout(Base):
    __tablename__ = "payouts"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, index=True)
    rider_id = Column(Integer, index=True)
    amount = Column(Float)
    payment_method = Column(String)
    razorpay_ref_id = Column(String, nullable=True)
    status = Column(String, default="initiated")
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
