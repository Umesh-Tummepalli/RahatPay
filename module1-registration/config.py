"""
config.py
---------
All configuration via environment variables.
Provide a .env file for local development.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from functools import lru_cache
from typing import Optional
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode


class Settings(BaseSettings):
    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "RahatPay Module 1"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

    # ── Database ──────────────────────────────────────────────────────────────
    # asyncpg driver required for async SQLAlchemy
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://rahatpay:rahatpay@localhost:5432/rahatpay",
        env="DATABASE_URL",
    )
    DB_ECHO: bool = Field(default=False, env="DB_ECHO")

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def convert_db_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgresql://"):
                v = "postgresql+asyncpg://" + v[len("postgresql://"):]
            elif v.startswith("postgres://"):
                v = "postgresql+asyncpg://" + v[len("postgres://"):]
            # asyncpg driver doesn't understand libpq-style sslmode query param.
            # If present (e.g. sslmode=require from Neon), strip it from the URL.
            try:
                parsed = urlparse(v)
                if parsed.query and "sslmode=" in parsed.query:
                    q = [(k, val) for (k, val) in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() != "sslmode"]
                    parsed = parsed._replace(query=urlencode(q))
                    v = urlunparse(parsed)
            except Exception:
                # Best-effort fallback: strip common patterns
                v = (
                    v.replace("?sslmode=disable", "")
                    .replace("&sslmode=disable", "")
                    .replace("?sslmode=require", "")
                    .replace("&sslmode=require", "")
                )
        return v

    # ── Firebase ──────────────────────────────────────────────────────────────
    FIREBASE_CREDENTIALS_PATH: Optional[str] = Field(
        default=None, env="FIREBASE_CREDENTIALS_PATH"
    )
    FIREBASE_MOCK_MODE: bool = Field(
        default=True,
        env="FIREBASE_MOCK_MODE",
        description="Use mock OTP (000000) when True — for dev/testing only",
    )

    # ── Module 2 Integration ──────────────────────────────────────────────────
    # When False, Module 2 functions are called directly (same process).
    # When True, fall back to sensible defaults (for standalone dev).
    MODULE2_MOCK_MODE: bool = Field(default=True, env="MODULE2_MOCK_MODE")

    # ── External APIs (Module 3 trigger polling) ─────────────────────────────
    # Optional here so Module 3 can load a shared Settings object without
    # Pydantic rejecting unknown env vars.
    OPENWEATHERMAP_API_KEY: Optional[str] = Field(default=None, env="OPENWEATHERMAP_API_KEY")

    # ── Business Constants ────────────────────────────────────────────────────
    PREMIUM_FLOOR: float = 15.0          # ₹15 minimum weekly premium
    PREMIUM_CAP_PERCENT: float = 0.035   # 3.5% of income maximum
    POLICY_CYCLE_WEEKS: int = 4          # Lock-in period in weeks
    MAX_PAYOUT_PER_CLAIM: float = 5000.0 # ₹5000 max per claim (DB constraint mirrors this)

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["*"]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_bool(cls, value):
        """Accept common environment-style debug values beyond strict booleans."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on", "debug", "development", "dev"}:
                return True
            if normalized in {"false", "0", "no", "off", "release", "production", "prod"}:
                return False
        return value

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Singleton for use throughout the app
settings = get_settings()

# ── Tier Configuration (static, owned by Module 1) ───────────────────────────
TIER_CONFIG = {
    "kavach": {
        "name": "Kavach",
        "display_name": "Kavach — Basic Protection",
        "tier_rate": 0.010,               # 1.0% of weekly income
        "weekly_payout_cap": 1500.00,     # ₹1,500/week
        "coverage_type": "income_disruption",
        "coverage_triggers": ["heavy_rain", "cyclone", "flood"],
        "description": "Entry-level coverage for basic income disruption events",
    },
    "suraksha": {
        "name": "Suraksha",
        "display_name": "Suraksha — Standard Protection",
        "tier_rate": 0.018,               # 1.8% of weekly income
        "weekly_payout_cap": 3000.00,     # ₹3,000/week
        "coverage_type": "income_disruption",
        "coverage_triggers": ["heavy_rain", "cyclone", "flood", "poor_aqi", "extreme_heat"],
        "description": "Mid-tier coverage including air quality and heat events",
    },
    "raksha": {
        "name": "Raksha",
        "display_name": "Raksha — Premium Protection",
        "tier_rate": 0.025,               # 2.5% of weekly income
        "weekly_payout_cap": 5000.00,     # ₹5,000/week
        "coverage_type": "income_disruption",
        "coverage_triggers": [
            "heavy_rain", "cyclone", "flood", "poor_aqi",
            "extreme_heat", "civic_disruption", "storm",
        ],
        "description": "Comprehensive protection for all disruption types",
    },
}

# ── Seasonal Factors (month → multiplier) ────────────────────────────────────
# High monsoon months get a higher factor (risk premium)
SEASONAL_FACTORS = {
    1: 0.90,   # January
    2: 0.88,   # February
    3: 0.92,   # March
    4: 0.95,   # April
    5: 1.00,   # May (pre-monsoon)
    6: 1.20,   # June (monsoon onset)
    7: 1.25,   # July (peak monsoon)
    8: 1.25,   # August (peak monsoon)
    9: 1.15,   # September (retreating monsoon)
    10: 1.05,  # October
    11: 0.95,  # November
    12: 0.90,  # December
}

# ── City-level Median Income (Module 2 fallback for seasoning riders) ─────────
CITY_MEDIAN_INCOME = {
    "Chennai":   3500.00,
    "Mumbai":    4200.00,
    "Bangalore": 4000.00,
    "Delhi":     3800.00,
}

CITY_MEDIAN_HOURS = {
    "Chennai":   40.0,
    "Mumbai":    42.0,
    "Bangalore": 41.0,
    "Delhi":     40.0,
}
