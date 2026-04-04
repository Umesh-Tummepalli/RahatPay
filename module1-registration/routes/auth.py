"""
routes/auth.py
--------------
OTP-based authentication endpoints using Firebase.

POST /auth/send-otp    — trigger SMS OTP
POST /auth/verify-otp  — verify OTP, return rider context
"""

import logging
import re
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends

from db.connection import get_db
from models.rider import Rider
from integrations.firebase_auth import (
    send_otp as firebase_send_otp,
    verify_otp as firebase_verify_otp,
    OTPInvalidError,
    OTPExpiredError,
    FirebaseError,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

# ── Pydantic schemas ──────────────────────────────────────────────────────────

class SendOTPRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Strip spaces/dashes before checking
        cleaned = v.strip().replace(" ", "").replace("-", "")
        # Accept +91XXXXXXXXXX or 10-digit or leading 0
        pattern = r"^(\+91|91|0)?[6-9]\d{9}$"
        if not re.match(pattern, cleaned):
            raise ValueError("Invalid Indian phone number format.")
        return v


class SendOTPResponse(BaseModel):
    session_info: str
    mock: bool
    message: str


class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str
    session_info: str | None = None

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        if not v.strip().isdigit() or len(v.strip()) != 6:
            raise ValueError("OTP must be a 6-digit number.")
        return v.strip()


class VerifyOTPResponse(BaseModel):
    verified: bool
    firebase_uid: str
    phone: str
    is_registered: bool
    rider_id: str | None = None
    rider_name: str | None = None
    message: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/send-otp",
    response_model=SendOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Send OTP to phone",
    description="Triggers Firebase Phone Auth to send a 6-digit OTP via SMS.",
)
async def send_otp(request: SendOTPRequest):
    """
    Send OTP to the given phone number.
    In mock mode (dev), OTP is always '000000'.
    """
    try:
        result = await firebase_send_otp(request.phone)
        return SendOTPResponse(**result)
    except FirebaseError as e:
        logger.error(f"send_otp Firebase error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OTP service unavailable: {str(e)}",
        )
    except Exception as e:
        logger.exception(f"send_otp unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP. Please try again.",
        )


@router.post(
    "/verify-otp",
    response_model=VerifyOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify OTP",
    description=(
        "Verifies the OTP. If the phone is registered, returns rider_id. "
        "If not, indicates a new user who should complete registration."
    ),
)
async def verify_otp(
    request: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify OTP and look up rider by phone.

    Returns:
    - is_registered=True + rider_id if phone exists in DB
    - is_registered=False if new user (must call /register)
    """
    try:
        firebase_result = await firebase_verify_otp(
            request.phone,
            request.otp,
            request.session_info,
        )
    except OTPExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP has expired. Please request a new one.",
        )
    except OTPInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP. Please try again.",
        )
    except FirebaseError as e:
        logger.error(f"verify_otp Firebase error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Authentication service unavailable: {str(e)}",
        )

    # Check if rider exists in DB
    # Normalize phone before lookup
    from integrations.firebase_auth import _normalize_phone
    normalized_phone = _normalize_phone(request.phone)

    # Try both the raw phone and normalized version
    stmt = select(Rider).where(
        Rider.phone.in_([request.phone, normalized_phone])
    )
    result = await db.execute(stmt)
    rider = result.scalar_one_or_none()

    if rider:
        return VerifyOTPResponse(
            verified=True,
            firebase_uid=firebase_result["uid"],
            phone=firebase_result["phone"],
            is_registered=True,
            rider_id=str(rider.id),
            rider_name=rider.name,
            message="Welcome back! You are already registered.",
        )

    return VerifyOTPResponse(
        verified=True,
        firebase_uid=firebase_result["uid"],
        phone=firebase_result["phone"],
        is_registered=False,
        rider_id=None,
        rider_name=None,
        message="Phone verified. Please complete registration.",
    )
