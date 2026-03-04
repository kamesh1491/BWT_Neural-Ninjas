"""
Seed Data Generator — creates realistic synthetic users, activity logs,
mood entries, and sample goals.
"""

import random
from datetime import datetime, timedelta
from models import init_db, get_session, User, ActivityLog, MoodEntry, UserGoal

# ── Configuration ──────────────────────────────────────────────────────────
NUM_USERS = 20
DAYS_BACK = 30
NORMAL_LOGS_PER_USER = (60, 120)
THREAT_LOGS_PER_USER = (120, 250)

DEPARTMENTS = [
    "Engineering", "Finance", "Human Resources", "Marketing",
    "Sales", "IT Security", "Legal", "Operations", "Research", "Executive",
]

ROLES = [
    "Software Engineer", "Data Analyst", "HR Manager", "Marketing Lead",
    "Sales Rep", "Security Analyst", "Legal Counsel", "DevOps Engineer",
    "Research Scientist", "VP of Operations",
]

FIRST_NAMES = [
    "James", "Maria", "Robert", "Linda", "David", "Sarah", "Michael",
    "Jennifer", "William", "Elizabeth", "Richard", "Jessica", "Thomas",
    "Karen", "Daniel", "Nancy", "Christopher", "Lisa", "Matthew", "Betty",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
]

DEVICES_NORMAL = ["Laptop-Corp-01", "Laptop-Corp-02", "Desktop-HQ-01", "Desktop-HQ-02"]
DEVICES_SUSPICIOUS = ["USB-External-Drive", "Personal-Laptop", "Unknown-Device", "Raspberry-Pi"]

LOCATIONS_NORMAL = ["HQ-Office", "Branch-NYC", "Branch-London", "VPN-Home"]
LOCATIONS_SUSPICIOUS = ["VPN-Russia", "VPN-China", "Unknown-Location", "Tor-Exit-Node"]

ACTIVITY_TYPES_NORMAL = ["login", "file_access", "email"]
ACTIVITY_TYPES_THREAT = ["login", "file_access", "email", "usb_usage", "failed_login"]


def _random_ts(base, offset_days, hour_range=(8, 18)):
    day = base - timedelta(days=offset_days)
    hour = random.randint(*hour_range)
    minute = random.randint(0, 59)
    return day.replace(hour=hour, minute=minute, second=random.randint(0, 59))


def _normal_ip():
    return f"10.0.{random.randint(1, 254)}.{random.randint(1, 254)}"


def _suspicious_ip():
    return f"{random.choice([185, 77, 91, 45])}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def _file_descriptions():
    files = [
        "Accessed /shared/reports/quarterly_revenue.xlsx",
        "Downloaded /confidential/employee_salaries.csv",
        "Opened /projects/alpha/design_spec.docx",
        "Copied /hr/performance_reviews_2025.pdf",
        "Read /engineering/source_code_archive.zip",
        "Viewed /finance/budget_forecast_2026.xlsx",
        "Accessed /legal/merger_documents.pdf",
        "Downloaded /research/patent_filings.docx",
        "Opened /marketing/campaign_strategy.pptx",
        "Exported /database/customer_records.csv",
    ]
    return random.choice(files)


MOOD_LABELS = {1: "Stressed", 2: "Anxious", 3: "Neutral", 4: "Calm", 5: "Energized"}

SAMPLE_GOALS = [
    {"title": "Complete Threat Analysis Project", "category": "project", "target_value": 100, "unit": "%", "days_left": 14},
    {"title": "Review all Critical Alerts", "category": "security", "target_value": 20, "unit": "alerts", "days_left": 7},
    {"title": "Maintain daily mood check-ins", "category": "wellness", "target_value": 30, "unit": "days", "days_left": 30},
    {"title": "Learn Python Security Automation", "category": "learning", "target_value": 10, "unit": "hours", "days_left": 21},
    {"title": "Reduce average stress below 3", "category": "wellness", "target_value": 3, "unit": "score", "days_left": 14},
    {"title": "Document network security policies", "category": "productivity", "target_value": 5, "unit": "docs", "days_left": 10},
]


def seed():
    """Generate and insert seed data."""
    init_db()
    session = get_session()

    # Clear existing data
    session.query(ActivityLog).delete()
    session.query(User).delete()
    session.query(MoodEntry).delete()
    session.query(UserGoal).delete()
    session.commit()

    now = datetime.utcnow()

    # ── Users & Activity Logs ──
    threat_indices = set(random.sample(range(NUM_USERS), 4))

    users = []
    for i in range(NUM_USERS):
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last  = LAST_NAMES[i % len(LAST_NAMES)]
        uname = f"{first.lower()}.{last.lower()}"
        dept  = DEPARTMENTS[i % len(DEPARTMENTS)]
        role  = ROLES[i % len(ROLES)]

        user = User(
            username=uname,
            full_name=f"{first} {last}",
            email=f"{uname}@acmecorp.com",
            department=dept,
            role=role,
            risk_score=0.0,
            risk_level="Low",
            is_active=True,
            created_at=now - timedelta(days=random.randint(90, 365)),
        )
        session.add(user)
        session.flush()
        users.append((user, i in threat_indices))

    for user, is_threat in users:
        count = random.randint(*(THREAT_LOGS_PER_USER if is_threat else NORMAL_LOGS_PER_USER))
        for _ in range(count):
            if is_threat and random.random() < 0.40:
                activity_type = random.choice(ACTIVITY_TYPES_THREAT)
                hour_range = random.choice([(0, 5), (22, 23), (1, 4)])
                ts = _random_ts(now, random.randint(0, DAYS_BACK), hour_range)
                device = random.choice(DEVICES_SUSPICIOUS + DEVICES_NORMAL)
                ip = _suspicious_ip() if random.random() < 0.5 else _normal_ip()
                location = random.choice(LOCATIONS_SUSPICIOUS + LOCATIONS_NORMAL)
            else:
                activity_type = random.choice(ACTIVITY_TYPES_NORMAL)
                ts = _random_ts(now, random.randint(0, DAYS_BACK), (8, 18))
                device = random.choice(DEVICES_NORMAL)
                ip = _normal_ip()
                location = random.choice(LOCATIONS_NORMAL)

            if activity_type == "login":
                desc = f"User logged in from {location}"
            elif activity_type == "failed_login":
                desc = f"Failed login attempt from {ip}"
            elif activity_type == "file_access":
                desc = _file_descriptions()
            elif activity_type == "usb_usage":
                desc = f"USB device '{random.choice(DEVICES_SUSPICIOUS)}' connected"
            elif activity_type == "email":
                desc = f"Sent email to {'external' if is_threat and random.random() < 0.3 else 'internal'} recipient"
            else:
                desc = "Unknown activity"

            session.add(ActivityLog(
                user_id=user.id, timestamp=ts, activity_type=activity_type,
                description=desc, ip_address=ip, device=device,
                is_anomaly=False, anomaly_score=0.0, location=location,
            ))

    # ── Mood Entries (30 days of synthetic mood data) ──
    for day_offset in range(DAYS_BACK):
        ts = now - timedelta(days=day_offset, hours=random.randint(8, 14), minutes=random.randint(0, 59))
        # Create a somewhat realistic mood pattern
        base_mood = 3
        if day_offset % 7 in (5, 6):  # weekends tend to be calmer
            base_mood = 4
        mood_score = max(1, min(5, base_mood + random.randint(-1, 1)))
        energy = max(1, min(5, 3 + random.randint(-2, 2)))
        stress = max(1, min(5, 3 + random.randint(-1, 2)))

        notes_options = [
            "", "Productive morning", "Feeling overwhelmed", "Good team meeting",
            "Deadline pressure", "Made good progress", "Need more sleep",
            "Great focus today", "Too many meetings", "Learning new things",
        ]

        session.add(MoodEntry(
            timestamp=ts,
            mood_score=mood_score,
            mood_label=MOOD_LABELS.get(mood_score, "Neutral"),
            energy_level=energy,
            stress_level=stress,
            notes=random.choice(notes_options),
        ))

    # ── Sample Goals ──
    for g in SAMPLE_GOALS:
        progress = random.uniform(10, 70)
        session.add(UserGoal(
            title=g["title"],
            category=g["category"],
            target_value=g["target_value"],
            current_value=round(progress / 100 * g["target_value"], 1),
            unit=g["unit"],
            deadline=now + timedelta(days=g["days_left"]),
            is_completed=False,
            created_at=now - timedelta(days=random.randint(3, 15)),
        ))

    session.commit()
    session.close()
    print(f"[OK] Seeded {NUM_USERS} users, {DAYS_BACK} mood entries, {len(SAMPLE_GOALS)} goals.")


if __name__ == "__main__":
    seed()
