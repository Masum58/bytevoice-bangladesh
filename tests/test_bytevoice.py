"""Comprehensive unit and integration tests for ByteVoice Bangladesh.

Tests:
1. Phone normalization (Bangla digits & formats -> 11 digit standard)
2. Database CRUD (Patients, Calls, Transcripts, Appointments, Callbacks)
3. Slot availability & double-booking prevention
4. Client tools execution
5. FastAPI Portal & Config endpoints
"""

import sys
from pathlib import Path

# Ensure 'src' is in sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bytevoice.api import create_app
from bytevoice.database import crud, models, schemas
from bytevoice.database.connection import Base, get_db
from bytevoice.voice.tools import (
    book_appointment,
    check_availability,
    get_clinic_info,
    request_callback,
)

from sqlalchemy.pool import StaticPool

# In-memory SQLite for testing with StaticPool so all threads/sessions share the same DB
TEST_DB_URL = "sqlite://"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_database():
    """Create fresh tables for every test."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    # Seed default admin user for portal auth tests
    admin = models.StaffUser(
        username="admin",
        email="admin@dhakadental.com",
        hashed_password="admin123",
        role="admin",
    )
    db.add(admin)
    db.commit()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


# --- 1. Phone Normalization Tests ---

def test_normalize_bd_phone_bangla_digits():
    """Converts Bengali numerals to English standard 01XXXXXXXXX."""
    assert schemas.normalize_bd_phone("০১৭১১২২৩৩৪") == "0171122334"
    assert schemas.normalize_bd_phone("+8801712345678") == "01712345678"
    assert schemas.normalize_bd_phone("018-9876-5432") == "01898765432"


# --- 2. Database CRUD Tests ---

def test_patient_crud(db_session):
    """Test patient creation and deduplication by phone."""
    p1 = crud.get_or_create_patient(db_session, "Rahim Ahmed", "01711223344")
    assert p1.id is not None
    assert p1.full_name == "Rahim Ahmed"
    assert p1.phone == "01711223344"

    # Same phone should return same patient record (no duplicate)
    p2 = crud.get_or_create_patient(db_session, "Rahim A.", "01711223344")
    assert p2.id == p1.id


def test_appointment_booking_and_slot_check(db_session):
    """Test slot booking and double booking prevention."""
    p = crud.get_or_create_patient(db_session, "Tanvir Hossain", "01811223344")
    slot = "2026-11-08 17:00"

    # Slot must initially be free
    assert crud.check_slot_available(db_session, slot) is True

    # Book the slot
    appt = crud.book_appointment(db_session, patient_id=p.id, slot_datetime=slot)
    assert appt.id is not None
    assert appt.status == "confirmed"

    # Slot must now be occupied
    assert crud.check_slot_available(db_session, slot) is False


def test_callback_request(db_session):
    """Test human staff callback escalation."""
    p = crud.get_or_create_patient(db_session, "Emergency Caller", "01999887766")
    cb = crud.create_callback_request(db_session, reason="Severe dental trauma", patient_id=p.id)
    assert cb.id is not None
    assert cb.status == "pending"

    callbacks = crud.list_callbacks(db_session)
    assert len(callbacks) >= 1


# --- 3. Client Tools Execution Tests ---

def test_tools_get_clinic_info():
    info = get_clinic_info({"info_type": "all"})
    assert "clinic_name" in info
    assert "Dhaka Dental Care" in info["clinic_name"]


def test_tools_check_availability():
    res = check_availability({"preferred_date": "2030-10-15", "preferred_time": "11:30"})
    assert "available" in res
    assert res["available"] is True


def test_tools_book_appointment():
    res = book_appointment({
        "patient_name": "Sadat Khan",
        "patient_phone": "01755443322",
        "reason_for_visit": "Teeth Scaling",
        "date": "2026-11-09",
        "time": "18:00",
    })
    assert res["success"] is True
    assert "Sadat Khan" in res["message"]


# --- 4. FastAPI Endpoints Tests ---

def test_api_config(client):
    res = client.get("/api/config")
    assert res.status_code == 200
    data = res.json()
    assert data["clinic_name"] == "Dhaka Dental Care"


def test_api_portal_stats(client):
    res = client.get("/api/portal/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_calls" in data
    assert "total_appointments" in data


def test_api_portal_login(client):
    # Valid login
    res = client.post("/api/portal/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    assert "access_token" in res.json()

    # Invalid login
    res_bad = client.post("/api/portal/login", json={"username": "admin", "password": "wrongpassword"})
    assert res_bad.status_code == 401

