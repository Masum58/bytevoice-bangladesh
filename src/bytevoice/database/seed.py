"""Database seeder for ByteVoice.

Pre-populates the database with:
1. Reviewer Admin Login (admin@dhakadental.com / admin123)
2. Dhaka Dental Care clinic settings (verified services, fees, hours, doctors)
3. Realistic test call records with full Bangla/English transcripts and bookings
   (Satisfies StrategyByte's requirement: 'Portal-e test call data age thekei thakbe').
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from bytevoice.database import models
from bytevoice.database.connection import Base, SessionLocal, engine


CLINIC_SERVICES = [
    {"name": "General Dental Consultation", "name_bn": "সাধারণ ডেন্টাল চেকআপ ও পরামর্শ", "fee": "500 BDT", "duration": "20 mins"},
    {"name": "Teeth Scaling & Polishing", "name_bn": "দাঁত স্কেলিং ও পলিশিং", "fee": "1,500 BDT", "duration": "45 mins"},
    {"name": "Dental Filling (Composite)", "name_bn": "দাঁতের ফিলিং", "fee": "1,200 - 2,000 BDT", "duration": "30 mins"},
    {"name": "Root Canal Treatment (RCT)", "name_bn": "রুট ক্যানেল ট্রিটমেন্ট", "fee": "4,500 - 6,000 BDT", "duration": "60 mins"},
    {"name": "Tooth Extraction", "name_bn": "দাঁত তোলা", "fee": "1,000 - 2,500 BDT", "duration": "30 mins"},
    {"name": "Teeth Whitening", "name_bn": "দাঁত সাদা করা", "fee": "8,000 BDT", "duration": "60 mins"},
]

CLINIC_DOCTORS = [
    {"name": "Dr. Tanvir Ahmed", "degrees": "BDS, PGT (Oral Surgery)", "specialty": "Chief Dental Surgeon", "available_days": "Sat-Thu (4 PM - 9 PM)"},
    {"name": "Dr. Nusrat Jahan", "degrees": "BDS, DDS (Orthodontics)", "specialty": "Cosmetic & Braces Specialist", "available_days": "Sun, Tue, Thu (10 AM - 3 PM)"},
]

CLINIC_FAQS = [
    {
        "question": "ক্লিনিকের ঠিকানা কোথায়?",
        "answer": "হাউজ ১২, রোড ৪, ধানমন্ডি, ঢাকা-১২০৫ (ধানমন্ডি লেকের কাছে, পপুলার ডায়াগনস্টিক সেন্টারের বিপরীতে)।",
    },
    {
        "question": "ক্লিনিক কখন খোলা থাকে?",
        "answer": "শনিবার থেকে বৃহস্পতিবার সকাল ১০:০০ টা থেকে রাত ৯:০০ টা পর্যন্ত এবং শুক্রবার বিকেল ৪:০০ টা থেকে রাত ৯:০০ টা পর্যন্ত খোলা থাকে।",
    },
    {
        "question": "পেমেন্ট কীভাবে করা যায়?",
        "answer": "ক্যাশ, বিকাশ (bKash), নগদ (Nagad) এবং ভিসা/মাস্টারকার্ড কার্ড পেমেন্ট নেওয়া হয়।",
    },
    {
        "question": "জরুরি দাঁতের ব্যথায় কী করব?",
        "answer": "তীব্র ব্যথায় সরাসরি ক্লিনিকে চলে এলে আমাদের অন-কল ডাক্তার অগ্রাধিকার ভিত্তিতে তাৎক্ষণিক প্রাথমিক চিকিৎসা দেন।",
    },
]


def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)


def seed_database():
    """Seed reviewer login, clinic info, and sample calls."""
    init_db()
    db = SessionLocal()

    try:
        # 1. Staff User (Reviewer Credentials)
        admin = db.query(models.StaffUser).filter(models.StaffUser.username == "admin").first()
        if not admin:
            admin = models.StaffUser(
                username="admin",
                email="admin@dhakadental.com",
                hashed_password="admin123",  # Clean demo password
                role="admin",
            )
            db.add(admin)

        # 2. Clinic Setting
        setting = db.query(models.ClinicSetting).first()
        if not setting:
            setting = models.ClinicSetting(
                clinic_name="Dhaka Dental Care",
                address="House 12, Road 4, Dhanmondi, Dhaka-1205",
                phone="+8801711223344",
                opening_hours="Sat-Thu: 10:00 AM - 09:00 PM | Fri: 04:00 PM - 09:00 PM",
                services_json=json.dumps(CLINIC_SERVICES, ensure_ascii=False),
                doctors_json=json.dumps(CLINIC_DOCTORS, ensure_ascii=False),
                faqs_json=json.dumps(CLINIC_FAQS, ensure_ascii=False),
            )
            db.add(setting)

        # 3. Sample Patient 1 (Rahim Ahmed - Booked Appointment)
        p1 = db.query(models.Patient).filter(models.Patient.phone == "01712345678").first()
        if not p1:
            p1 = models.Patient(
                full_name="Rahim Ahmed",
                phone="01712345678",
                email="rahim.ahmed@gmail.com",
                created_at=datetime.utcnow() - timedelta(hours=3),
            )
            db.add(p1)
            db.flush()

            # Call for Rahim
            c1_id = "demo-call-rahim-001"
            c1 = models.Call(
                id=c1_id,
                patient_id=p1.id,
                started_at=datetime.utcnow() - timedelta(hours=3),
                ended_at=datetime.utcnow() - timedelta(hours=3) + timedelta(seconds=98),
                duration_s=98,
                status="booked",
                summary="রোগী রহিম আহমেদ তীব্র দাঁতে ব্যথার জন্য আগামী রবিবার বিকেল ৫টায় ডা. তানভীর আহমেদের সাথে অ্যাপয়েন্টমেন্ট বুক করেছেন।",
            )
            db.add(c1)

            # Transcripts for Call 1
            t1_turns = [
                ("ai", "আসসালামু আলাইকুম, ঢাকা ডেন্টাল কেয়ারে স্বাগতম। আমি কীভাবে আপনাকে সাহায্য করতে পারি?", "Hello, welcome to Dhaka Dental Care. How may I assist you?", 0),
                ("patient", "আমার নাম রহিম আহমেদ। আমার দাঁতে খুব ব্যথা, একটা অ্যাপয়েন্টমেন্ট লাগবে।", "My name is Rahim Ahmed. I have severe toothache, I need an appointment.", 1),
                ("ai", "জি রহিম সাহেব, দাঁতের ব্যথার জন্য অবশ্যই অ্যাপয়েন্টমেন্ট করে দিচ্ছি। আপনার ফোন নম্বরটি কি ০১৭ ১২ ৩৪ ৫৬ ৭৮?", "Yes Mr. Rahim, I will certainly arrange an appointment for toothache. Is your phone number 017 12 34 56 78?", 2),
                ("patient", "জি, ঠিক আছে। আগামী রবিবার বিকেলে ডাক্তার দেখাতে পারব?", "Yes, that's correct. Can I see the doctor next Sunday evening?", 3),
                ("ai", "জি, আগামী রবিবার বিকেল ৫টায় ডা. তানভীর আহমেদের একটি স্লট খালি আছে। আমি কি বুক করে দেব?", "Yes, Dr. Tanvir Ahmed has a slot available next Sunday at 5:00 PM. Shall I book it?", 4),
                ("patient", "হ্যাঁ, রবিবার বিকেল ৫টা কনফার্ম করেন।", "Yes, please confirm Sunday at 5:00 PM.", 5),
                ("ai", "ধন্যবাদ রহিম সাহেব। আগামী রবিবার বিকেল ৫টায় আপনার অ্যাপয়েন্টমেন্ট কনফার্ম করা হলো। আমাদের ঠিকানা ধানমন্ডি ৪ নম্বর রোড। সুস্থ থাকুন!", "Thank you Mr. Rahim. Your appointment is confirmed for next Sunday at 5:00 PM. Our address is Dhanmondi Road 4. Stay well!", 6),
            ]
            for spk, bn, en, idx in t1_turns:
                db.add(models.TranscriptTurn(
                    call_id=c1_id,
                    speaker=spk,
                    text_bn=bn,
                    text_en=en,
                    order_index=idx,
                    ts=datetime.utcnow() - timedelta(hours=3) + timedelta(seconds=idx * 14),
                ))

            # Extraction for Call 1
            db.add(models.CallExtraction(
                call_id=c1_id,
                reason_for_visit="Toothache (তীব্র দাঁতে ব্যথা)",
                preferred_datetime="Next Sunday, 5:00 PM",
                intent="booking",
                urgency="normal",
                notes="Patient requested Sunday evening slot for toothache treatment.",
            ))

            # Appointment for Call 1
            db.add(models.Appointment(
                patient_id=p1.id,
                call_id=c1_id,
                doctor_name="Dr. Tanvir Ahmed (BDS, PGT)",
                service_name="Toothache Consultation & Treatment",
                slot_datetime="2026-11-08 17:00",
                status="confirmed",
                notes="Booked via Bangla Voice Receptionist",
            ))

        # 4. Sample Patient 2 (Shirin Akter - Enquiry Call)
        p2 = db.query(models.Patient).filter(models.Patient.phone == "01898765432").first()
        if not p2:
            p2 = models.Patient(
                full_name="Shirin Akter",
                phone="01898765432",
                created_at=datetime.utcnow() - timedelta(hours=6),
            )
            db.add(p2)
            db.flush()

            c2_id = "demo-call-shirin-002"
            c2 = models.Call(
                id=c2_id,
                patient_id=p2.id,
                started_at=datetime.utcnow() - timedelta(hours=6),
                ended_at=datetime.utcnow() - timedelta(hours=6) + timedelta(seconds=65),
                duration_s=65,
                status="enquiry",
                summary="রোগী শিরিন আক্তার দাঁত স্কেলিং ও পলিশিংয়ের খরচ এবং সময়সূচি জানতে ফোন করেছিলেন। তথ্য প্রদান করা হয়েছে।",
            )
            db.add(c2)

            t2_turns = [
                ("ai", "আসসালামু আলাইকুম, ঢাকা ডেন্টাল কেয়ারে স্বাগতম। আমি আপনাকে কীভাবে সাহায্য করতে পারি?", "Hello, welcome to Dhaka Dental Care. How can I help you?", 0),
                ("patient", "আপনাদের এখানে দাঁত স্কেলিং করতে কত খরচ পড়বে?", "How much does teeth scaling cost at your clinic?", 1),
                ("ai", "আমাদের এখানে আল্ট্রাসনিক স্কেলিং ও পলিশিংয়ের মোট খরচ ১,৫০০ টাকা। এতে সাধারণত ৩০ থেকে ৪৫ মিনিট সময় লাগে।", "At our clinic, ultrasonic scaling and polishing costs 1,500 BDT. It typically takes 30 to 45 minutes.", 2),
                ("patient", "আচ্ছা ঠিক আছে, আমি পরিবারের সাথে কথা বলে পরে বুক করব। ধন্যবাদ।", "Okay great, I will discuss with my family and book later. Thank you.", 3),
                ("ai", "জি অবশ্যই শিরিন আপা। যেকোনো প্রয়োজনে আমাদের ফোন করতে পারেন। শুভ দিন!", "Certainly Ms. Shirin. Feel free to call us anytime. Have a good day!", 4),
            ]
            for spk, bn, en, idx in t2_turns:
                db.add(models.TranscriptTurn(
                    call_id=c2_id,
                    speaker=spk,
                    text_bn=bn,
                    text_en=en,
                    order_index=idx,
                    ts=datetime.utcnow() - timedelta(hours=6) + timedelta(seconds=idx * 13),
                ))

            db.add(models.CallExtraction(
                call_id=c2_id,
                reason_for_visit="Teeth Scaling & Polishing Fee Enquiry",
                preferred_datetime=None,
                intent="enquiry",
                urgency="normal",
                notes="Patient asked for scaling prices. Will call back for booking.",
            ))

        # 5. Sample Patient 3 (Kamal Hossain - Callback Needed)
        p3 = db.query(models.Patient).filter(models.Patient.phone == "01911223344").first()
        if not p3:
            p3 = models.Patient(
                full_name="Kamal Hossain",
                phone="01911223344",
                created_at=datetime.utcnow() - timedelta(hours=12),
            )
            db.add(p3)
            db.flush()

            c3_id = "demo-call-kamal-003"
            c3 = models.Call(
                id=c3_id,
                patient_id=p3.id,
                started_at=datetime.utcnow() - timedelta(hours=12),
                ended_at=datetime.utcnow() - timedelta(hours=12) + timedelta(seconds=75),
                duration_s=75,
                status="follow_up_needed",
                summary="রোগীর সড়ক দুর্ঘটনায় দাঁত ভেঙে রক্তক্ষরণ হচ্ছে। জরুরি চিকিৎসার জন্য স্টাফ কলব্যাক রিকোয়েস্ট তৈরি করা হয়েছে।",
            )
            db.add(c3)

            db.add(models.CallExtraction(
                call_id=c3_id,
                reason_for_visit="Dental Trauma & Bleeding",
                preferred_datetime="Immediate",
                intent="complaint",
                urgency="emergency",
                notes="Urgent dental trauma callback needed.",
            ))

            db.add(models.CallbackRequest(
                call_id=c3_id,
                patient_id=p3.id,
                reason="জরুরি দাঁতের আঘাত ও রক্তপাত। রোগীকে দ্রুত হাসপাতালে আসার জন্য কলব্যাক দেওয়া প্রয়োজন।",
                status="pending",
                created_at=datetime.utcnow() - timedelta(hours=12),
            ))

        db.commit()
        print("ByteVoice database successfully seeded with clinic data, admin reviewer, and sample calls.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

