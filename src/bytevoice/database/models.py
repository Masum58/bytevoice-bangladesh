"""SQLAlchemy models for ByteVoice Healthcare Receptionist System.

Matches StrategyByte's brief and case study entities:
- StaffUser: Portal reviewer and clinic staff accounts
- Patient: Patients registry with normalized phone numbers
- Call: Phone/WebRTC call sessions and outcomes
- TranscriptTurn: Turn-by-turn dialogue lines with timestamp and speaker label
- CallExtraction: AI-extracted clinical intent and visit reason
- Appointment: Confirmed clinic appointment bookings
- ClinicSetting: Reliable grounded clinic info (hours, doctors, fees)
- CallbackRequest: Human handover and follow-up queue
"""

from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from bytevoice.database.connection import Base


class StaffUser(Base):
    """Staff user for the clinic admin portal."""
    __tablename__ = "staff_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="receptionist")  # admin, receptionist
    created_at = Column(DateTime, default=datetime.utcnow)


class Patient(Base):
    """Patient records with normalized phone numbers."""
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), index=True, nullable=False)
    phone = Column(String(20), index=True, nullable=False)
    email = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    calls = relationship("Call", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")
    callbacks = relationship("CallbackRequest", back_populates="patient")


class Call(Base):
    """Call session records."""
    __tablename__ = "calls"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    duration_s = Column(Integer, default=0)
    status = Column(String(30), default="in_progress")  # in_progress, booked, enquiry, follow_up_needed, incomplete, failed
    recording_url = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    patient = relationship("Patient", back_populates="calls")
    transcripts = relationship("TranscriptTurn", back_populates="call", cascade="all, delete-orphan", order_by="TranscriptTurn.order_index")
    extraction = relationship("CallExtraction", back_populates="call", uselist=False, cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="call")


class TranscriptTurn(Base):
    """Turn-by-turn spoken dialogue lines."""
    __tablename__ = "transcript_turns"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String(36), ForeignKey("calls.id"), nullable=False, index=True)
    speaker = Column(String(20), nullable=False)  # "ai" or "patient" or "system"
    text_bn = Column(Text, nullable=False)
    text_en = Column(Text, nullable=True)
    ts = Column(DateTime, default=datetime.utcnow)
    order_index = Column(Integer, default=0)

    # Relationships
    call = relationship("Call", back_populates="transcripts")


class CallExtraction(Base):
    """Structured data extracted by AI from the conversation."""
    __tablename__ = "call_extractions"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String(36), ForeignKey("calls.id"), unique=True, nullable=False, index=True)
    reason_for_visit = Column(String(255), nullable=True)
    preferred_datetime = Column(String(100), nullable=True)
    intent = Column(String(50), nullable=True)  # booking, rescheduling, enquiry, complaint, wrong_number
    urgency = Column(String(20), default="normal")  # normal, emergency
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    call = relationship("Call", back_populates="extraction")


class Appointment(Base):
    """Confirmed clinic appointments."""
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    call_id = Column(String(36), ForeignKey("calls.id"), nullable=True)
    doctor_name = Column(String(100), default="Dr. Tanvir Ahmed (BDS, PGT)")
    service_name = Column(String(100), default="General Dental Consultation")
    slot_datetime = Column(String(50), nullable=False)  # e.g., "2026-11-08 17:00"
    status = Column(String(20), default="confirmed")  # confirmed, cancelled, rescheduled, completed
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    call = relationship("Call", back_populates="appointments")


class ClinicSetting(Base):
    """Clinic identity and verified operational data."""
    __tablename__ = "clinic_settings"

    id = Column(Integer, primary_key=True, index=True)
    clinic_name = Column(String(100), default="Dhaka Dental Care")
    address = Column(String(255), default="House 12, Road 4, Dhanmondi, Dhaka-1205")
    phone = Column(String(20), default="+8801711000000")
    opening_hours = Column(String(255), default="Sat-Thu: 10:00 AM - 09:00 PM | Fri: 04:00 PM - 09:00 PM")
    services_json = Column(Text, nullable=False)
    doctors_json = Column(Text, nullable=False)
    faqs_json = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CallbackRequest(Base):
    """Queue for human receptionists to follow up with patient."""
    __tablename__ = "callback_requests"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String(36), ForeignKey("calls.id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # pending, contacted, resolved
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    patient = relationship("Patient", back_populates="callbacks")

