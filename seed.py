"""
Seed script for the campus_complaints prototype.
Creates tables, an admin user, student user, sample complaints, suggestions, and notifications.
Run with:
    python -m campus_complaints.seed
"""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from . import models, database
from .utils.security import get_password_hash
from .utils.ml import classify_category, detect_priority, analyze_complaint_and_generate_solutions

def create_or_get_user(db, email, password, role, admin_id=None):
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        if admin_id and not existing.admin_id:
            existing.admin_id = admin_id
            db.commit()
        return existing
    user = models.User(
        email=email,
        admin_id=admin_id,
        hashed_password=get_password_hash(password),
        is_verified=True,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def main():
    database.init_db()
    db = database.SessionLocal()

    admin = create_or_get_user(db, "admin@college.edu", "adminpass", models.UserRole.admin, admin_id="ADM-001")
    student = create_or_get_user(db, "student@college.edu", "studentpass", models.UserRole.student)

    if db.query(models.Complaint).count() == 0:
        samples = [
            ("Leaking water pipe in the chemistry lab", "A major water pipe is leaking rapidly and flooding the hallway near lab 204.", models.SubmissionType.complaint, models.ComplaintStatus.resolved),
            ("Dirty restroom on the 3rd floor", "The washroom floor is wet, trash bins are overflowing, and soap is missing.", models.SubmissionType.complaint, models.ComplaintStatus.in_progress),
            ("Wi-Fi signal drops frequently in library", "The student Wi-Fi disconnects every 5 minutes in the central library reading hall.", models.SubmissionType.complaint, models.ComplaintStatus.under_review),
            ("Missing reference textbooks for CS101", "The required algorithm textbooks are not available in the college library.", models.SubmissionType.complaint, models.ComplaintStatus.submitted),
            ("Extend Central Library weekend hours to 11 PM", "Provide quiet air-conditioned study spaces for project teams during weekends.", models.SubmissionType.suggestion, models.ComplaintStatus.under_review),
            ("Pipe leaking near chemistry lab entrance", "Water is pooling outside chem lab door, similar to the leak inside.", models.SubmissionType.complaint, models.ComplaintStatus.in_progress),
        ]

        for title, desc, sub_type, status in samples:
            cat = classify_category(title + " " + desc)
            prio = detect_priority(title + " " + desc) if sub_type == models.SubmissionType.complaint else models.PriorityLevel.low
            cat_str = cat.value if hasattr(cat, "value") else str(cat)
            prio_str = prio.value if hasattr(prio, "value") else str(prio)
            sub_str = sub_type.value if hasattr(sub_type, "value") else str(sub_type)

            ai_info = analyze_complaint_and_generate_solutions(title, desc, cat_str, prio_str)

            complaint = models.Complaint(
                title=title,
                description=desc,
                submission_type=sub_str,
                category=cat_str,
                priority=prio_str,
                status=status.value if hasattr(status, "value") else str(status),
                reporter_id=student.id,
                ai_analysis=ai_info["ai_analysis"],
                ai_solution_suggestion=ai_info["ai_solution_suggestion"],
                assigned_department=ai_info["assigned_department"],
                estimated_turnaround=ai_info["estimated_turnaround"]
            )
            db.add(complaint)
        db.commit()

        # Seed sample notifications for student
        first_comp = db.query(models.Complaint).first()
        if first_comp:
            notif1 = models.Notification(
                user_id=student.id,
                complaint_id=first_comp.id,
                title=f"🎉 Issue Resolved: #{first_comp.id}",
                message=f"Great news! Your complaint '{first_comp.title}' has been successfully resolved by the campus maintenance department."
            )
            notif2 = models.Notification(
                user_id=student.id,
                title="💡 Suggestion Received",
                message="Your campus suggestion has been forwarded to the Academic Facilities Committee for evaluation."
            )
            db.add(notif1)
            db.add(notif2)
            db.commit()

    print("Demo data successfully created/verified.")
    print("Admin credentials -> Admin ID / Email: ADM-001 or admin@college.edu | Password: adminpass")
    print("Student credentials -> Email: student@college.edu | Password: studentpass")

if __name__ == "__main__":
    main()
