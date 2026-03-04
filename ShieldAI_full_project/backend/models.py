"""
Database models for the Insider Threat Detection System.
Uses SQLAlchemy ORM with SQLite backend.
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, Boolean, Text,
    ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

# ---------------------------------------------------------------------------
# User — represents a monitored employee / account
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String(80), unique=True, nullable=False)
    full_name     = Column(String(150), nullable=False)
    email         = Column(String(150), nullable=False)
    department    = Column(String(100), nullable=False)
    role          = Column(String(100), nullable=False)
    risk_score    = Column(Float, default=0.0)          # 0‑100
    risk_level    = Column(String(20), default="Low")    # Low / Medium / High / Critical
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    activities = relationship("ActivityLog", back_populates="user", lazy="dynamic")
    alerts     = relationship("Alert", back_populates="user", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "full_name": self.full_name,
            "email": self.email,
            "department": self.department,
            "role": self.role,
            "risk_score": round(self.risk_score, 1),
            "risk_level": self.risk_level,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# ActivityLog — individual events (logins, file access, etc.)
# ---------------------------------------------------------------------------
class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp       = Column(DateTime, nullable=False)
    activity_type   = Column(String(50), nullable=False)   # login, file_access, usb_usage, email, failed_login
    description     = Column(Text)
    ip_address      = Column(String(45))
    device          = Column(String(100))
    is_anomaly      = Column(Boolean, default=False)
    anomaly_score   = Column(Float, default=0.0)
    location        = Column(String(100))

    user = relationship("User", back_populates="activities")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "activity_type": self.activity_type,
            "description": self.description,
            "ip_address": self.ip_address,
            "device": self.device,
            "is_anomaly": self.is_anomaly,
            "anomaly_score": round(self.anomaly_score, 3),
            "location": self.location,
        }


# ---------------------------------------------------------------------------
# Alert — generated when the ML engine flags an anomaly
# ---------------------------------------------------------------------------
class Alert(Base):
    __tablename__ = "alerts"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp   = Column(DateTime, default=datetime.utcnow)
    severity    = Column(String(20), nullable=False)       # Low / Medium / High / Critical
    category    = Column(String(60), nullable=False)       # odd_hour_login, excessive_file_access, ...
    title       = Column(String(200), nullable=False)
    description = Column(Text)
    is_resolved = Column(Boolean, default=False)

    user = relationship("User", back_populates="alerts")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "full_name": self.user.full_name if self.user else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "is_resolved": self.is_resolved,
        }


# ---------------------------------------------------------------------------
# MoodEntry — daily mood check-ins
# ---------------------------------------------------------------------------
class MoodEntry(Base):
    __tablename__ = "mood_entries"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    timestamp     = Column(DateTime, default=datetime.utcnow, nullable=False)
    mood_score    = Column(Integer, nullable=False)           # 1-5
    mood_label    = Column(String(30), nullable=False)        # Stressed/Anxious/Neutral/Calm/Energized
    energy_level  = Column(Integer, default=3)                # 1-5
    stress_level  = Column(Integer, default=3)                # 1-5
    notes         = Column(Text, default="")

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "mood_score": self.mood_score,
            "mood_label": self.mood_label,
            "energy_level": self.energy_level,
            "stress_level": self.stress_level,
            "notes": self.notes or "",
        }


# ---------------------------------------------------------------------------
# UserGoal — personal productivity / security / wellness goals
# ---------------------------------------------------------------------------
class UserGoal(Base):
    __tablename__ = "user_goals"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    title          = Column(String(200), nullable=False)
    category       = Column(String(30), nullable=False)       # security / productivity / wellness
    target_value   = Column(Float, default=100.0)
    current_value  = Column(Float, default=0.0)
    unit           = Column(String(30), default="%")
    deadline       = Column(DateTime, nullable=True)
    is_completed   = Column(Boolean, default=False)
    created_at     = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "unit": self.unit,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "is_completed": self.is_completed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "progress": round(min(self.current_value / max(self.target_value, 1) * 100, 100), 1),
        }


# ---------------------------------------------------------------------------
# Engine / Session helpers
# ---------------------------------------------------------------------------
DATABASE_URL = "sqlite:///threat_detection.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Create all tables."""
    Base.metadata.create_all(engine)

def get_session():
    return SessionLocal()
