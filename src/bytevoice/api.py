"""FastAPI backend server for ByteVoice Bangladesh.

Provides:
- Voice token minting (/api/voice/token) for in-browser WebRTC conversation
- Realtime tool dispatching (/api/tools/{name})
- Call completion & transcript syncing (/api/voice/complete)
- Clinical staff data portal APIs (/api/portal/*)
- Reviewer authentication (/api/portal/login)
- Static file serving for the Next.js frontend console
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Annotated, Any

import httpx
from fastapi import Body, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from bytevoice.config import get_settings
from bytevoice.database import crud, models, schemas
from bytevoice.database.connection import get_db
from bytevoice.database.seed import seed_database
from bytevoice.voice.persona import FIRST_MESSAGE
from bytevoice.voice.tools import CLIENT_TOOL_HANDLERS

TOKEN_URL = "https://api.elevenlabs.io/v1/convai/conversation/token"

_REPO_ROOT = Path(__file__).resolve().parents[2]


def web_dir() -> Path:
    return Path(os.environ.get("BYTEVOICE_WEB_DIR") or _REPO_ROOT / "web" / "out")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ByteVoice Bangladesh - Dental Clinic Receptionist API",
        description="Backend API powering the Bangla AI Receptionist and Clinical Staff Portal for Dhaka Dental Care.",
        version="1.0.0",
    )

    # Enable CORS for Next.js dev server on port 3000
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def on_startup():
        """Ensure database tables exist and seed demo data on startup."""
        seed_database()

    # --- Config & Voice Session Endpoints ---

    @app.get("/api/config")
    def config() -> dict:
        """Returns environment capability and clinic profile."""
        settings = get_settings()
        return {
            "voice_ok": settings.has_voice,
            "clinic_name": "Dhaka Dental Care",
            "voice_hint": "ElevenLabs configured" if settings.has_voice else "Add ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID to .env",
            "has_agent": bool(settings.elevenlabs_agent_id),
        }

    @app.post("/api/voice/token")
    def voice_token() -> dict:
        """Mint a short-lived conversation token for the browser WebRTC session."""
        settings = get_settings()
        if not settings.has_voice:
            # If no API key is provided, provide a clear instructional error
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ElevenLabs API credentials not configured. Please add ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID to .env",
            )

        try:
            resp = httpx.get(
                TOKEN_URL,
                params={"agent_id": settings.elevenlabs_agent_id},
                headers={"xi-api-key": settings.elevenlabs_api_key.get_secret_value()},
                timeout=15,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"ElevenLabs connection error: {exc}") from exc

        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Token request failed ({resp.status_code}): {resp.text[:200]}",
            )

        token = resp.json().get("token")
        if not token:
            raise HTTPException(status_code=502, detail="ElevenLabs returned no token")

        return {
            "token": token,
            "first_message": FIRST_MESSAGE,
        }

    @app.post("/api/tools/{name}")
    def call_tool(name: str, parameters: Annotated[dict | None, Body()] = None) -> dict:
        """Execute a client tool called by the ElevenLabs voice agent."""
        handler = CLIENT_TOOL_HANDLERS.get(name)
        if handler is None:
            raise HTTPException(status_code=404, detail=f"Unknown tool: {name}")
        return handler(parameters or {})

    @app.post("/api/voice/complete")
    def complete_call(
        payload: schemas.CallEndRequest,
        db: Session = Depends(get_db),
    ) -> dict:
        """Finalize call session when user hangs up, saving transcripts and extractions."""
        call_id = payload.id or str(uuid.uuid4())
        call = crud.finalize_call(
            db=db,
            call_id=call_id,
            duration_s=payload.duration_s,
            status=payload.status,
            summary=payload.summary,
            recording_url=payload.recording_url,
            transcripts=payload.transcripts,
            extraction=payload.extraction,
        )
        return {"success": True, "call_id": call.id, "status": call.status}

    # --- Staff Data Portal Endpoints ---

    @app.post("/api/portal/login")
    def portal_login(
        credentials: schemas.StaffLoginRequest,
        db: Session = Depends(get_db),
    ) -> schemas.StaffLoginResponse:
        """Authenticate reviewer or staff member."""
        user = crud.verify_staff_login(db, credentials.username, credentials.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password. Default demo login is admin / admin123",
            )
        return schemas.StaffLoginResponse(
            access_token=f"demo-token-{user.id}",
            username=user.username,
            role=user.role,
        )

    @app.get("/api/portal/stats")
    def portal_stats(db: Session = Depends(get_db)) -> dict:
        """High-level metrics for the clinic management dashboard."""
        total_calls = db.query(models.Call).count()
        booked_calls = db.query(models.Call).filter(models.Call.status == "booked").count()
        enquiry_calls = db.query(models.Call).filter(models.Call.status == "enquiry").count()
        follow_up_calls = db.query(models.Call).filter(models.Call.status == "follow_up_needed").count()
        total_appointments = db.query(models.Appointment).filter(models.Appointment.status != "cancelled").count()
        pending_callbacks = db.query(models.CallbackRequest).filter(models.CallbackRequest.status == "pending").count()

        return {
            "total_calls": total_calls,
            "booked_calls": booked_calls,
            "enquiry_calls": enquiry_calls,
            "follow_up_calls": follow_up_calls,
            "total_appointments": total_appointments,
            "pending_callbacks": pending_callbacks,
        }

    @app.get("/api/portal/calls")
    def get_calls(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        status: str | None = None,
        search: str | None = None,
        db: Session = Depends(get_db),
    ) -> dict:
        """List call sessions with search and status filtering."""
        calls, total = crud.list_calls(db, skip=skip, limit=limit, status=status, search=search)
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "calls": [
                {
                    "id": c.id,
                    "caller_name": c.patient.full_name if c.patient else "Anonymous Caller",
                    "caller_phone": c.patient.phone if c.patient else "N/A",
                    "started_at": c.started_at.isoformat(),
                    "duration_s": c.duration_s,
                    "status": c.status,
                    "summary": c.summary or "General consultation inquiry",
                }
                for c in calls
            ],
        }

    @app.get("/api/portal/calls/{call_id}")
    def get_call_detail(call_id: str, db: Session = Depends(get_db)) -> dict:
        """Retrieve full details of a single call: audio, transcript, extraction, and appointment."""
        call = crud.get_call_detail(db, call_id)
        if not call:
            raise HTTPException(status_code=404, detail="Call record not found")

        return {
            "id": call.id,
            "caller_name": call.patient.full_name if call.patient else "Anonymous",
            "caller_phone": call.patient.phone if call.patient else "N/A",
            "started_at": call.started_at.isoformat(),
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "duration_s": call.duration_s,
            "status": call.status,
            "summary": call.summary,
            "recording_url": call.recording_url,
            "extraction": {
                "reason_for_visit": call.extraction.reason_for_visit if call.extraction else None,
                "preferred_datetime": call.extraction.preferred_datetime if call.extraction else None,
                "intent": call.extraction.intent if call.extraction else None,
                "urgency": call.extraction.urgency if call.extraction else "normal",
                "notes": call.extraction.notes if call.extraction else None,
            } if call.extraction else None,
            "transcripts": [
                {
                    "speaker": t.speaker,
                    "text_bn": t.text_bn,
                    "text_en": t.text_en,
                    "ts": t.ts.isoformat(),
                }
                for t in call.transcripts
            ],
            "appointments": [
                {
                    "id": a.id,
                    "slot": a.slot_datetime,
                    "doctor": a.doctor_name,
                    "service": a.service_name,
                    "status": a.status,
                }
                for a in call.appointments
            ],
        }

    @app.get("/api/portal/appointments")
    def get_appointments(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        db: Session = Depends(get_db),
    ) -> dict:
        """List confirmed clinic appointments."""
        appointments, total = crud.list_appointments(db, skip=skip, limit=limit)
        return {
            "total": total,
            "appointments": [
                {
                    "id": a.id,
                    "patient_name": a.patient.full_name if a.patient else "Unknown",
                    "patient_phone": a.patient.phone if a.patient else "N/A",
                    "slot_datetime": a.slot_datetime,
                    "service_name": a.service_name,
                    "doctor_name": a.doctor_name,
                    "status": a.status,
                    "notes": a.notes,
                    "created_at": a.created_at.isoformat(),
                }
                for a in appointments
            ],
        }

    @app.get("/api/portal/callbacks")
    def get_callbacks(
        status: str | None = None,
        db: Session = Depends(get_db),
    ) -> list[dict]:
        """List human receptionist callback tasks."""
        callbacks = crud.list_callbacks(db, status=status)
        return [
            {
                "id": cb.id,
                "patient_name": cb.patient.full_name if cb.patient else "Unknown",
                "patient_phone": cb.patient.phone if cb.patient else "N/A",
                "reason": cb.reason,
                "status": cb.status,
                "created_at": cb.created_at.isoformat(),
            }
            for cb in callbacks
        ]

    @app.get("/api/portal/clinic")
    def get_clinic_info(db: Session = Depends(get_db)) -> dict:
        """Return full clinic configuration."""
        setting = crud.get_clinic_settings(db)
        if not setting:
            raise HTTPException(status_code=404, detail="Clinic settings not initialized")
        import json
        return {
            "clinic_name": setting.clinic_name,
            "address": setting.address,
            "phone": setting.phone,
            "opening_hours": setting.opening_hours,
            "services": json.loads(setting.services_json),
            "doctors": json.loads(setting.doctors_json),
            "faqs": json.loads(setting.faqs_json),
        }

    # Mount static frontend export if available
    console_path = web_dir()
    if (console_path / "index.html").exists():
        app.mount("/", StaticFiles(directory=console_path, html=True), name="frontend")

    return app


# Module-level app instance for standard 'uvicorn bytevoice.api:app' runners
app = create_app()


def main():
    """Run FastAPI development server with uvicorn."""
    import uvicorn
    settings = get_settings()
    uvicorn.run("bytevoice.api:create_app", host="0.0.0.0", port=settings.api_port, reload=True, factory=True)


if __name__ == "__main__":
    main()

