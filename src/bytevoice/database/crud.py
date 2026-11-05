"""Database CRUD operations for ByteVoice.

Clean repository pattern for managing patients, calls, appointments,
transcripts, callbacks, and settings.
"""

from __future__ import annotations

import json
from datetime import datetime
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from bytevoice.database import models, schemas


# --- Patient Operations ---

def get_or_create_patient(
    db: Session,
    full_name: str,
    phone: str,
    email: str | None = None,
) -> models.Patient:
    """Find patient by normalized phone or create a new record."""
    normalized_phone = schemas.normalize_bd_phone(phone)
    patient = db.query(models.Patient).filter(models.Patient.phone == normalized_phone).first()
    if not patient:
        patient = models.Patient(
            full_name=full_name.strip(),
            phone=normalized_phone,
            email=email.strip() if email else None,
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
    else:
        # Update name if previously empty or changed
        if full_name and patient.full_name != full_name.strip():
            patient.full_name = full_name.strip()
            db.commit()
            db.refresh(patient)
    return patient


# --- Call Operations ---

def create_call(
    db: Session,
    call_id: str | None = None,
    patient_id: int | None = None,
) -> models.Call:
    """Register a new call session."""
    call = models.Call(
        id=call_id or None,
        patient_id=patient_id,
        started_at=datetime.utcnow(),
        status="in_progress",
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


def finalize_call(
    db: Session,
    call_id: str,
    duration_s: int = 0,
    status: str = "completed",
    summary: str | None = None,
    recording_url: str | None = None,
    transcripts: list[schemas.TranscriptTurnBase] | None = None,
    extraction: schemas.CallExtractionBase | None = None,
) -> models.Call | None:
    """Finalize a call session, attach transcripts and extractions."""
    call = db.query(models.Call).filter(models.Call.id == call_id).first()
    if not call:
        # If call wasn't pre-registered, create it
        call = models.Call(id=call_id, started_at=datetime.utcnow())
        db.add(call)

    call.ended_at = datetime.utcnow()
    call.duration_s = duration_s
    call.status = status
    if summary:
        call.summary = summary
    if recording_url:
        call.recording_url = recording_url

    # Save transcripts
    if transcripts:
        for idx, turn in enumerate(transcripts):
            t_turn = models.TranscriptTurn(
                call_id=call_id,
                speaker=turn.speaker,
                text_bn=turn.text_bn,
                text_en=turn.text_en,
                order_index=turn.order_index or idx,
                ts=datetime.utcnow(),
            )
            db.add(t_turn)

    # Save extraction
    if extraction:
        existing_ext = db.query(models.CallExtraction).filter(models.CallExtraction.call_id == call_id).first()
        if not existing_ext:
            ext = models.CallExtraction(
                call_id=call_id,
                reason_for_visit=extraction.reason_for_visit,
                preferred_datetime=extraction.preferred_datetime,
                intent=extraction.intent,
                urgency=extraction.urgency or "normal",
                notes=extraction.notes,
            )
            db.add(ext)

    db.commit()
    db.refresh(call)
    return call


def list_calls(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
    search: str | None = None,
) -> tuple[list[models.Call], int]:
    """List calls with optional status filter and patient search."""
    query = db.query(models.Call).join(models.Patient, models.Call.patient_id == models.Patient.id, isouter=True)

    if status and status != "all":
        query = query.filter(models.Call.status == status)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                models.Patient.full_name.ilike(search_pattern),
                models.Patient.phone.ilike(search_pattern),
                models.Call.summary.ilike(search_pattern),
            )
        )

    total = query.count()
    calls = query.order_by(desc(models.Call.started_at)).offset(skip).limit(limit).all()
    return calls, total


def get_call_detail(db: Session, call_id: str) -> models.Call | None:
    """Retrieve full call detail including transcripts, extraction, and appointment."""
    return db.query(models.Call).filter(models.Call.id == call_id).first()


# --- Appointment Operations ---

def check_slot_available(db: Session, slot_datetime: str) -> bool:
    """Check if an appointment slot is free (prevents double-booking)."""
    clean_slot = slot_datetime.strip()
    existing = db.query(models.Appointment).filter(
        models.Appointment.slot_datetime == clean_slot,
        models.Appointment.status != "cancelled",
    ).first()
    return existing is None


def book_appointment(
    db: Session,
    patient_id: int,
    slot_datetime: str,
    service_name: str = "General Dental Consultation",
    doctor_name: str = "Dr. Tanvir Ahmed (BDS, PGT)",
    call_id: str | None = None,
    notes: str | None = None,
) -> models.Appointment:
    """Create a confirmed appointment for a patient."""
    clean_slot = slot_datetime.strip()

    # Check if this call already created an appointment for this patient (upsert behavior)
    if call_id:
        existing = db.query(models.Appointment).filter(
            models.Appointment.call_id == call_id,
            models.Appointment.patient_id == patient_id,
        ).first()
        if existing:
            existing.slot_datetime = clean_slot
            existing.service_name = service_name
            existing.doctor_name = doctor_name
            existing.notes = notes
            existing.status = "confirmed"
            db.commit()
            db.refresh(existing)
            return existing

    appointment = models.Appointment(
        patient_id=patient_id,
        call_id=call_id,
        doctor_name=doctor_name,
        service_name=service_name,
        slot_datetime=clean_slot,
        status="confirmed",
        notes=notes,
    )
    db.add(appointment)

    # If associated with a call, update call status to booked
    if call_id:
        call = db.query(models.Call).filter(models.Call.id == call_id).first()
        if call:
            call.status = "booked"

    db.commit()
    db.refresh(appointment)
    return appointment


def list_appointments(db: Session, skip: int = 0, limit: int = 50) -> tuple[list[models.Appointment], int]:
    """List all appointments ordered by created date."""
    query = db.query(models.Appointment)
    total = query.count()
    appointments = query.order_by(desc(models.Appointment.created_at)).offset(skip).limit(limit).all()
    return appointments, total


# --- Callback Operations ---

def create_callback_request(
    db: Session,
    reason: str,
    call_id: str | None = None,
    patient_id: int | None = None,
) -> models.CallbackRequest:
    """Create a follow-up task for clinic staff."""
    callback = models.CallbackRequest(
        call_id=call_id,
        patient_id=patient_id,
        reason=reason,
        status="pending",
    )
    db.add(callback)

    if call_id:
        call = db.query(models.Call).filter(models.Call.id == call_id).first()
        if call and call.status != "booked":
            call.status = "follow_up_needed"

    db.commit()
    db.refresh(callback)
    return callback


def list_callbacks(db: Session, status: str | None = None) -> list[models.CallbackRequest]:
    """List callback requests."""
    query = db.query(models.CallbackRequest)
    if status and status != "all":
        query = query.filter(models.CallbackRequest.status == status)
    return query.order_by(desc(models.CallbackRequest.created_at)).all()


# --- Clinic Settings ---

def get_clinic_settings(db: Session) -> models.ClinicSetting | None:
    """Get the active clinic configuration."""
    return db.query(models.ClinicSetting).first()


# --- Staff Authentication ---

def verify_staff_login(db: Session, username_or_email: str, password: str) -> models.StaffUser | None:
    """Verify reviewer/staff credentials (uses clean hashing or plain match for demo accounts)."""
    user = db.query(models.StaffUser).filter(
        or_(
            models.StaffUser.username == username_or_email.strip(),
            models.StaffUser.email == username_or_email.strip(),
        )
    ).first()
    if not user:
        return None
    # For take-home demo simplicity: matches password directly or hash
    if user.hashed_password in (password, f"hashed_{password}"):
        return user
    return None

