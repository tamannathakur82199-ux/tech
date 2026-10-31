from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from .database import Base

class UserRole(str, enum.Enum):
    student = "student"
    faculty = "faculty"
    staff = "staff"
    admin = "admin"

class SubmissionType(str, enum.Enum):
    complaint = "Complaint"
    suggestion = "Suggestion"

class ComplaintStatus(str, enum.Enum):
    submitted = "Submitted"
    under_review = "Under Review"
    in_progress = "In Progress"
    resolved = "Resolved"

class PriorityLevel(str, enum.Enum):
    low = "Low"
    medium = "Medium"
    high = "High"

class Category(str, enum.Enum):
    infrastructure = "Infrastructure"
    sanitation = "Sanitation"
    academics = "Academics"
    student_services = "Student Services"
    other = "Other"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    verification_code = Column(String, nullable=True)
    role = Column(String, default="student")
    created_at = Column(DateTime, default=datetime.utcnow)

    complaints = relationship("Complaint", back_populates="reporter")
    notifications = relationship("Notification", back_populates="user", order_by="desc(Notification.created_at)")

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    submission_type = Column(String, default="Complaint")
    category = Column(String, default="Other")
    image_path = Column(String, nullable=True)
    status = Column(String, default="Submitted")
    priority = Column(String, default="Low")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reporter_id = Column(Integer, ForeignKey("users.id"))
    duplicate_of_id = Column(Integer, ForeignKey("complaints.id"), nullable=True)

    # AI Diagnostics & Admin Suggestions
    ai_analysis = Column(Text, nullable=True)
    ai_solution_suggestion = Column(Text, nullable=True)
    assigned_department = Column(String, default="Campus Estates & Facilities")
    estimated_turnaround = Column(String, default="24-48 Hours")

    # Concern-Based Classification & AI Clustering
    concern_type = Column(String, default="General Campus Maintenance")
    concern_severity = Column(String, default="Moderate")
    key_indicators = Column(String, nullable=True)
    cluster_tag = Column(String, nullable=True)
    similarity_score = Column(Integer, default=0)

    reporter = relationship("User", back_populates="complaints")
    duplicate_of = relationship("Complaint", remote_side=[id])

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")
    complaint = relationship("Complaint")

class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    admin = relationship("User", foreign_keys=[admin_id])
    user = relationship("User", foreign_keys=[user_id])
