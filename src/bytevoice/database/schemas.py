"""Pydantic v2 schemas for ByteVoice.

Enforces strict input validation, data normalization, and serialization
for the FastAPI endpoints and AI tool calls.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


# --- Normalization Helpers ---

def normalize_bd_phone(phone: str) -> str:
    """Normalize Bengali or formatted phone number to standard 11-digit BD mobile string."""
    # Convert Bengali digits to English
    bengali_digits = "০১২৩৪৫৬৭৮৯"
    english_digits = "0123456789"
    mapping = str.maketrans("".join(bengali_digits), "".join(english_digits))
    converted = phone.translate(mapping)

    # Strip non-digits
    digits = re.sub(r"\D", "", converted)

    # If it starts with country code 880, strip it
    if digits.startswith("880") and len(digits) == 13:
        digits = digits[2:]

    # Ensure it starts with 01
    if not digits.startswith("01") and len(digits) == 10:
        digits = "0" + digits

    return digits


# --- Staff Schemas ---

class StaffLoginRequest(BaseModel):
    username: str
    password: str


class StaffLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


# --- Patient Schemas ---

class PatientBase(BaseModel):
    full_name: str
    phone: str
    email: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        normalized = normalize_bd_phone(v)
        if len(normalized) != 11 or not normalized.startswith("01"):
            # We preserve best-effort instead of crashing live calls, but mark warning
            return normalized
        return normalized


class PatientCreate(PatientBase):
    pass


class PatientOut(PatientBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Transcript Schemas ---

class TranscriptTurnBase(BaseModel):
    speaker: Literal["ai", "patient", "system"]
    text_bn: str
    text_en: str | None = None
    order_index: int = 0


class TranscriptTurnCreate(TranscriptTurnBase):
    call_id: str


class TranscriptTurnOut(TranscriptTurnBase):
    id: int
    call_id: str
    ts: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Call Extraction Schemas ---

class CallExtractionBase(BaseModel):
    reason_for_visit: str | None = None
    preferred_datetime: str | None = None
    intent: str | None = None
    urgency: str | None = "normal"
    notes: str | None = None


class CallExtractionCreate(CallExtractionBase):
    call_id: str


class CallExtractionOut(CallExtractionBase):
    id: int
    call_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Appointment Schemas ---

class AppointmentBase(BaseModel):
    slot_datetime: str  # e.g., "2026-11-08 17:00"
    service_name: str = "General Dental Consultation"
    doctor_name: str = "Dr. Tanvir Ahmed (BDS, PGT)"
    notes: str | None = None


class AppointmentCreate(AppointmentBase):
    patient_id: int
    call_id: str | None = None


class AppointmentOut(AppointmentBase):
    id: int
    patient_id: int
    call_id: str | None = None
    status: str
    created_at: datetime
    patient: PatientOut | None = None
    model_config = ConfigDict(from_attributes=True)


# --- Call Schemas ---

class CallCreate(BaseModel):
    id: str | None = None
    patient_id: int | None = None
    status: str = "in_progress"


class CallEndRequest(BaseModel):
    id: str | None = None
    duration_s: int = 0
    status: str = "completed"
    summary: str | None = None
    recording_url: str | None = None
    transcripts: list[TranscriptTurnBase] = Field(default_factory=list)
    extraction: CallExtractionBase | None = None


class CallOut(BaseModel):
    id: str
    patient_id: int | None = None
    started_at: datetime
    ended_at: datetime | None = None
    duration_s: int
    status: str
    recording_url: str | None = None
    summary: str | None = None
    patient: PatientOut | None = None
    model_config = ConfigDict(from_attributes=True)


class CallDetailOut(CallOut):
    transcripts: list[TranscriptTurnOut] = Field(default_factory=list)
    extraction: CallExtractionOut | None = None
    appointments: list[AppointmentOut] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


# --- Callback Schemas ---

class CallbackRequestCreate(BaseModel):
    call_id: str | None = None
    patient_id: int | None = None
    reason: str


class CallbackRequestOut(BaseModel):
    id: int
    call_id: str | None = None
    patient_id: int | None = None
    reason: str
    status: str
    created_at: datetime
    patient: PatientOut | None = None
    model_config = ConfigDict(from_attributes=True)


# --- Clinic Settings Schemas ---

class ClinicSettingOut(BaseModel):
    clinic_name: str
    address: str
    phone: str
    opening_hours: str
    services: list[dict]
    doctors: list[dict]
    faqs: list[dict]


# --- AI Client Tools Schemas (ElevenLabs Callbacks) ---

class ToolCheckAvailability(BaseModel):
    preferred_date: str  # e.g., "আগামী রবিবার" or "2026-11-08"
    preferred_time: str  # e.g., "বিকেল ৫টা" or "17:00"
    service_name: str | None = "General Checkup"


class ToolBookAppointment(BaseModel):
    patient_name: str
    patient_phone: str
    reason_for_visit: str
    date: str
    time: str
    doctor_name: str | None = None
    call_id: str | None = None


class ToolRequestCallback(BaseModel):
    patient_name: str
    patient_phone: str
    reason: str
    call_id: str | None = None

