"""
config.py  (Module 3 — Triggers & Claims)
-----------------------------------------
Loads environment variables from Module 3's own .env file.
No dependency on Module 1's config.
No emoji characters (Windows cp1252 safe).
"""

import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Always load .env from Module 3's own directory, regardless of CWD.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_env_path = os.path.join(_BASE_DIR, ".env")
load_dotenv(_env_path, override=False)

_raw_db_url = os.getenv("DATABASE_URL")

if not _raw_db_url:
    logger.warning(
        "DATABASE_URL is not set. "
        "Create a .env file in module3-triggers-claims/ with:\n"
        "  DATABASE_URL=postgresql+asyncpg://postgres:<PASSWORD>@localhost:5432/rahatpay\n"
        "Falling back to SQLite for local dev only."
    )

# Safe fallback so the import never hard-crashes (e.g. during testing).
DATABASE_URL: str = _raw_db_url or "sqlite+aiosqlite:///./module3_dev.db"

logger.info("Module 3 config loaded. DB driver: %s", DATABASE_URL.split("://")[0])

# ── Tier Configuration (read-only copy; Module 1 is the authoritative source) ─
TIER_CONFIG = {
    "kavach": {
        "name": "Kavach",
        "display_name": "Kavach — Basic Protection",
        "tier_rate": 0.010,
        "weekly_payout_cap": 1500.00,
        "coverage_type": "income_disruption",
        "coverage_triggers": ["heavy_rain", "cyclone", "flood"],
        "description": "Entry-level coverage for basic income disruption events",
    },
    "suraksha": {
        "name": "Suraksha",
        "display_name": "Suraksha — Standard Protection",
        "tier_rate": 0.018,
        "weekly_payout_cap": 3000.00,
        "coverage_type": "income_disruption",
        "coverage_triggers": ["heavy_rain", "cyclone", "flood", "poor_aqi", "extreme_heat"],
        "description": "Mid-tier coverage including air quality and heat events",
    },
    "raksha": {
        "name": "Raksha",
        "display_name": "Raksha — Premium Protection",
        "tier_rate": 0.025,
        "weekly_payout_cap": 5000.00,
        "coverage_type": "income_disruption",
        "coverage_triggers": [
            "heavy_rain", "cyclone", "flood", "poor_aqi",
            "extreme_heat", "civic_disruption", "storm",
        ],
        "description": "Comprehensive protection for all disruption types",
    },
}

# ── Pydantic Settings (optional — only loaded if pydantic-settings is available) ─
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
    from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

    class Settings(BaseSettings):
        DATABASE_URL: str = Field(default=DATABASE_URL, env="DATABASE_URL")
        DB_ECHO: bool = Field(default=False, env="DB_ECHO")
        DEBUG: bool = Field(default=False, env="DEBUG")
        ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
        OPENWEATHERMAP_API_KEY: str | None = Field(default=None, env="OPENWEATHERMAP_API_KEY")

        class Config:
            env_file = _env_path
            case_sensitive = True

    from functools import lru_cache

    @lru_cache()
    def get_settings() -> Settings:
        return Settings()

    settings = get_settings()

except ImportError:
    # pydantic-settings not installed — use plain dataclass fallback
    class _FallbackSettings:  # type: ignore[no-redef]
        DATABASE_URL = DATABASE_URL
        DB_ECHO = False
        DEBUG = False
        ENVIRONMENT = "development"
        OPENWEATHERMAP_API_KEY = None

    settings = _FallbackSettings()  # type: ignore[assignment]
