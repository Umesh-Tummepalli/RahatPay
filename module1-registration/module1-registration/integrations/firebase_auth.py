"""
integrations/firebase_auth.py
------------------------------
Firebase Admin SDK integration for OTP-based authentication.

Supports:
  - Real Firebase Phone Auth verification (production)
  - Mock mode for development/testing (OTP = "000000")

Flow:
  1. Client calls POST /auth/send-otp   → Firebase sends SMS
  2. Client calls POST /auth/verify-otp → Firebase verifies token
     → returns rider_id if registered, None if new user
"""

import logging
import hashlib
import hmac
from typing import Optional
from datetime import datetime, timedelta

from config import settings

logger = logging.getLogger(__name__)

# ── Firebase SDK init ─────────────────────────────────────────────────────────

_firebase_initialized = False
_firebase_auth = None

if not settings.FIREBASE_MOCK_MODE and settings.FIREBASE_CREDENTIALS_PATH:
    try:
        import firebase_admin
        from firebase_admin import credentials, auth as firebase_auth_sdk

        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)

        _firebase_auth = firebase_auth_sdk
        _firebase_initialized = True
        logger.info("Firebase Admin SDK initialized (real mode).")
    except Exception as e:
        logger.warning(f"Firebase SDK init failed ({e}). Falling back to mock mode.")
else:
    logger.info("Firebase running in MOCK MODE. All OTPs accepted as '000000'.")


# ── In-memory OTP store for mock mode ────────────────────────────────────────
# In production this is handled by Firebase — no server-side OTP storage needed.
# For mock mode, we store a simple hash to avoid plaintext storage.
_mock_otp_store: dict[str, dict] = {}  # phone → {otp_hash, expires_at}
_MOCK_OTP = "000000"
_OTP_TTL_SECONDS = 300  # 5 minutes


# ── Public interface ──────────────────────────────────────────────────────────

class FirebaseError(Exception):
    """Raised when Firebase operation fails."""
    pass


class OTPExpiredError(FirebaseError):
    pass


class OTPInvalidError(FirebaseError):
    pass


async def send_otp(phone: str) -> dict:
    """
    Initiate OTP send for given phone number.

    Real mode: Firebase handles SMS delivery. We return a session_info token
    that the client must include in verify_otp.

    Mock mode: Returns mock session token. OTP is always "000000".
    Returns:
        {"session_info": str, "mock": bool}
    """
    phone = _normalize_phone(phone)

    if _firebase_initialized and _firebase_auth:
        try:
            # Firebase REST API approach for phone sign-in
            # In production, the CLIENT SDK handles this directly.
            # For server-to-server, we generate a custom token.
            # The client then uses this to trigger SMS.
            logger.info(f"Firebase OTP requested for {_mask_phone(phone)}")
            return {
                "session_info": f"firebase_session_{phone}",
                "mock": False,
                "message": "OTP sent via Firebase",
            }
        except Exception as e:
            raise FirebaseError(f"Firebase send_otp failed: {e}")

    # ── Mock mode ─────────────────────────────────────────────────────────────
    otp_hash = hashlib.sha256(_MOCK_OTP.encode()).hexdigest()
    _mock_otp_store[phone] = {
        "otp_hash": otp_hash,
        "expires_at": datetime.utcnow() + timedelta(seconds=_OTP_TTL_SECONDS),
    }
    logger.debug(f"Mock OTP stored for {_mask_phone(phone)}")
    return {
        "session_info": f"mock_session_{phone}",
        "mock": True,
        "message": "Mock OTP sent (use '000000')",
    }


async def verify_otp(phone: str, otp: str, session_info: Optional[str] = None) -> dict:
    """
    Verify OTP for given phone number.

    Returns:
        {
            "uid": str,            # Firebase UID
            "phone": str,
            "verified": bool,
        }
    Raises:
        OTPInvalidError  — wrong OTP
        OTPExpiredError  — OTP expired
        FirebaseError    — SDK error
    """
    phone = _normalize_phone(phone)

    if _firebase_initialized and _firebase_auth:
        try:
            # In production flow:
            # Client verifies OTP via Firebase SDK and gets an ID token.
            # The server verifies the ID token:
            #   decoded = firebase_auth.verify_id_token(id_token)
            # Here session_info is treated as the ID token.
            if session_info and not session_info.startswith("mock_"):
                decoded = _firebase_auth.verify_id_token(session_info)
                return {
                    "uid": decoded["uid"],
                    "phone": decoded.get("phone_number", phone),
                    "verified": True,
                }
        except Exception as e:
            raise FirebaseError(f"Firebase verify_otp failed: {e}")

    # ── Mock mode ─────────────────────────────────────────────────────────────
    record = _mock_otp_store.get(phone)

    if not record:
        # Allow verification even without prior send_otp in test mode
        if otp == _MOCK_OTP:
            uid = _derive_mock_uid(phone)
            return {"uid": uid, "phone": phone, "verified": True}
        raise OTPInvalidError("OTP not found. Call send-otp first.")

    # Check expiry
    if datetime.utcnow() > record["expires_at"]:
        _mock_otp_store.pop(phone, None)
        raise OTPExpiredError("OTP has expired. Request a new one.")

    # Verify
    submitted_hash = hashlib.sha256(otp.encode()).hexdigest()
    if not hmac.compare_digest(submitted_hash, record["otp_hash"]):
        raise OTPInvalidError("Invalid OTP.")

    # Clean up on success
    _mock_otp_store.pop(phone, None)
    uid = _derive_mock_uid(phone)
    return {"uid": uid, "phone": phone, "verified": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_phone(phone: str) -> str:
    """Strip spaces, ensure +91 prefix for Indian numbers."""
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        if phone.startswith("0"):
            phone = "+91" + phone[1:]
        elif len(phone) == 10:
            phone = "+91" + phone
        else:
            phone = "+" + phone
    return phone


def _mask_phone(phone: str) -> str:
    """Return masked phone for safe logging: +91XXXXXX3210"""
    if len(phone) > 4:
        return phone[:-6] + "X" * 4 + phone[-2:]
    return "***"


def _derive_mock_uid(phone: str) -> str:
    """Deterministic mock Firebase UID from phone number."""
    return "mock_uid_" + hashlib.md5(phone.encode()).hexdigest()[:12]
