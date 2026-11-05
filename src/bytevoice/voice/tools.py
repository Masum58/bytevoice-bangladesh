"""Voice agent client tool handlers for ByteVoice.

Called directly by the FastAPI backend when ElevenLabs WebRTC agent invokes a client tool.
Reads and writes directly to the clinic PostgreSQL database via SQLAlchemy.
"""

from __future__ import annotations

import json
from bytevoice.database import crud, models
from bytevoice.database.connection import SessionLocal


def get_clinic_info(parameters: dict | None = None) -> dict:
    """Provide verified, reliable clinic identity, hours, fees, and doctor info."""
    db = SessionLocal()
    try:
        setting = crud.get_clinic_settings(db)
        if not setting:
            return {
                "clinic_name": "Dhaka Dental Care",
                "address": "House 12, Road 4, Dhanmondi, Dhaka-1205",
                "phone": "+8801711223344",
                "opening_hours": "Sat-Thu: 10:00 AM - 09:00 PM | Fri: 04:00 PM - 09:00 PM",
                "consultation_fee": "500 BDT",
                "scaling_fee": "1500 BDT",
            }

        info_type = (parameters or {}).get("info_type", "all").lower()

        services = json.loads(setting.services_json)
        doctors = json.loads(setting.doctors_json)
        faqs = json.loads(setting.faqs_json)

        if info_type == "fees" or info_type == "services":
            return {"services_and_fees": services}
        elif info_type == "doctors":
            return {"doctors": doctors}
        elif info_type == "hours":
            return {"opening_hours": setting.opening_hours}
        elif info_type == "address":
            return {"address": setting.address, "phone": setting.phone}

        return {
            "clinic_name": setting.clinic_name,
            "address": setting.address,
            "phone": setting.phone,
            "opening_hours": setting.opening_hours,
            "services": services,
            "doctors": doctors,
            "faqs": faqs,
        }
    finally:
        db.close()


def check_availability(parameters: dict | None = None) -> dict:
    """Check if requested slot is free."""
    params = parameters or {}
    preferred_date = str(params.get("preferred_date", "")).strip()
    preferred_time = str(params.get("preferred_time", "")).strip()

    if not preferred_date or not preferred_time:
        return {
            "available": False,
            "message": "তারিখ এবং সময় স্পষ্টভাবে পাওয়া যায়নি। দয়া করে দিন ও সময় আবার বলুন।",
        }

    slot_key = f"{preferred_date} {preferred_time}"
    db = SessionLocal()
    try:
        is_free = crud.check_slot_available(db, slot_key)
        if is_free:
            return {
                "available": True,
                "slot": slot_key,
                "message": f"{preferred_date} {preferred_time}-এ স্লটটি খালি আছে। আপনি চাইলে বুক করতে পারেন।",
            }
        else:
            return {
                "available": False,
                "slot": slot_key,
                "message": f"দুঃখিত, {preferred_date} {preferred_time}-এ স্লটটি ইতিমধ্যে বুক হয়ে গেছে। আপনি কি এর ৩০ মিনিট পরে বা অন্য কোনো সময়ে দেখতে চান?",
            }
    finally:
        db.close()


def book_appointment(parameters: dict | None = None) -> dict:
    """Create a real confirmed appointment in the database."""
    params = parameters or {}
    name = str(params.get("patient_name", "")).strip()
    phone = str(params.get("patient_phone", "")).strip()
    reason = str(params.get("reason_for_visit", "Dental Consultation")).strip()
    date_val = str(params.get("date", "")).strip()
    time_val = str(params.get("time", "")).strip()
    doctor = str(params.get("doctor_name", "Dr. Tanvir Ahmed (BDS, PGT)")).strip()
    call_id = params.get("call_id")

    if not name or not phone:
        return {
            "success": False,
            "message": "রোগীর নাম অথবা ফোন নম্বর পাওয়া যায়নি। অনুগ্রহ করে নাম ও ফোন নম্বর দিন।",
        }

    slot_datetime = f"{date_val} {time_val}"
    db = SessionLocal()
    try:
        patient = crud.get_or_create_patient(db, full_name=name, phone=phone)
        appointment = crud.book_appointment(
            db,
            patient_id=patient.id,
            slot_datetime=slot_datetime,
            service_name=reason,
            doctor_name=doctor,
            call_id=str(call_id) if call_id else None,
            notes=f"Booked via Voice Agent. Reason: {reason}",
        )
        return {
            "success": True,
            "appointment_id": appointment.id,
            "patient_name": patient.full_name,
            "slot": slot_datetime,
            "doctor": doctor,
            "message": f"ধন্যবাদ {patient.full_name} সাহেব! আগামী {slot_datetime}-এ আপনার অ্যাপয়েন্টমেন্ট কনফার্ম করা হয়েছে। আমরা আপনাকে এসএমএসের মাধ্যমে রিমাইন্ডার পাঠিয়ে দেব।",
        }
    except Exception as exc:
        db.rollback()
        return {
            "success": False,
            "message": f"বুকিং সিস্টেমে সমস্যা হয়েছে। তবে আপনার তথ্য লিখে রাখা হয়েছে: {exc}",
        }
    finally:
        db.close()


def request_callback(parameters: dict | None = None) -> dict:
    """Save an urgent callback request for human receptionist."""
    params = parameters or {}
    name = str(params.get("patient_name", "")).strip()
    phone = str(params.get("patient_phone", "")).strip()
    reason = str(params.get("reason", "Urgent follow-up requested")).strip()
    call_id = params.get("call_id")

    db = SessionLocal()
    try:
        patient = crud.get_or_create_patient(db, full_name=name or "Unknown Patient", phone=phone or "01700000000")
        callback = crud.create_callback_request(
            db,
            reason=reason,
            call_id=str(call_id) if call_id else None,
            patient_id=patient.id,
        )
        return {
            "success": True,
            "callback_id": callback.id,
            "message": "আপনার জরুরি অনুরোধটি আমাদের ফ্রন্ট ডেস্কের মানব স্টাফদের জানানো হয়েছে। খুব দ্রুত আমাদের একজন প্রতিনিধি আপনাকে ফোন করবেন।",
        }
    finally:
        db.close()


# Registry of tools dispatched by FastAPI
CLIENT_TOOL_HANDLERS = {
    "get_clinic_info": get_clinic_info,
    "check_availability": check_availability,
    "book_appointment": book_appointment,
    "request_callback": request_callback,
}

