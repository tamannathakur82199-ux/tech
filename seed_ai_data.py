import os
from campus_complaints.database import SessionLocal, init_db
from campus_complaints import models
from campus_complaints.utils.ml import (
    classify_category, detect_priority, classify_concern,
    analyze_complaint_and_generate_solutions, find_duplicate_with_details
)

init_db()
db = SessionLocal()

print("1. Updating existing complaints with AI concern profiles & clusters...")
all_c = db.query(models.Complaint).all()
for c in all_c:
    insights = analyze_complaint_and_generate_solutions(
        c.title, c.description, str(c.category or "Other"), str(c.priority or "Low")
    )
    c.ai_analysis = insights["ai_analysis"]
    c.ai_solution_suggestion = insights["ai_solution_suggestion"]
    c.assigned_department = insights["assigned_department"]
    c.estimated_turnaround = insights["estimated_turnaround"]
    c.concern_type = insights["concern_type"]
    c.concern_severity = insights["concern_severity"]
    c.key_indicators = insights["key_indicators"]
    
    # Check duplicate
    dup_id, sim_score, cluster_tag = find_duplicate_with_details(
        db, c.title, c.description, str(c.category or "Other"), exclude_id=c.id
    )
    if dup_id:
        c.duplicate_of_id = dup_id
        c.similarity_score = sim_score
        c.cluster_tag = cluster_tag
        parent = db.query(models.Complaint).filter(models.Complaint.id == dup_id).first()
        if parent and not parent.cluster_tag:
            parent.cluster_tag = cluster_tag
db.commit()

print("Existing records updated.")

# Check if we want to add a few more realistic complaints to demonstrate all concern types and clusters
test_complaints = [
    {
        "title": "Severe water leakage flooding Chemistry Lab floor 2",
        "description": "The ceiling pipe is gushing water again right above the chemical storage racks in chemistry lab 2nd floor. Students are slipping.",
        "sub_type": "Complaint",
        "reporter_email": "student1@college.edu"
    },
    {
        "title": "Exposed high voltage wires and spark near Main Auditorium",
        "description": "There are open electric wires hanging from the junction box near the auditorium exit. Saw sparks flying when lights turned on. Very dangerous for passing students.",
        "sub_type": "Complaint",
        "reporter_email": "student2@college.edu"
    },
    {
        "title": "Central Library 2nd floor Wi-Fi keeps disconnecting during research",
        "description": "The campus wifi router on library second floor disconnects every 5 minutes. Cannot access research papers or online portal.",
        "sub_type": "Complaint",
        "reporter_email": "student3@college.edu"
    },
    {
        "title": "Hostel Block B washrooms have severe drain blockage and foul smell",
        "description": "All three toilets in Hostel Block B ground floor are overflowing and clogged. Stagnant contaminated water is causing mosquito breeding and unbearable stink.",
        "sub_type": "Complaint",
        "reporter_email": "student4@college.edu"
    },
    {
        "title": "Digital projector broken in Lecture Hall 4 during Midterm classes",
        "description": "The ceiling projector in Lecture Hall 4 has a blown bulb and flickers pink. Faculty cannot project slides for the exam preparation sessions.",
        "sub_type": "Complaint",
        "reporter_email": "student5@college.edu"
    },
    {
        "title": "Install high-speed water bottle refilling stations across campus",
        "description": "Suggestion to replace old drinking coolers with modern sensor-based touchless water bottle refilling stations in all academic blocks.",
        "sub_type": "Suggestion",
        "reporter_email": "student6@college.edu"
    }
]

# Ensure reporters exist
for item in test_complaints:
    email = item["reporter_email"]
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        from campus_complaints.utils.security import get_password_hash
        user = models.User(
            email=email,
            hashed_password=get_password_hash("password123"),
            is_verified=True,
            role="student"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Check if complaint with this title already exists
    existing = db.query(models.Complaint).filter(models.Complaint.title == item["title"]).first()
    if not existing:
        cat = classify_category(item["title"] + " " + item["description"])
        prio = detect_priority(item["title"] + " " + item["description"])
        cat_str = cat.value if hasattr(cat, "value") else str(cat)
        prio_str = prio.value if hasattr(prio, "value") else str(prio)
        
        insights = analyze_complaint_and_generate_solutions(item["title"], item["description"], cat_str, prio_str)
        
        new_c = models.Complaint(
            title=item["title"],
            description=item["description"],
            submission_type=item["sub_type"],
            category=cat_str,
            priority=prio_str,
            reporter_id=user.id,
            status="Submitted",
            ai_analysis=insights["ai_analysis"],
            ai_solution_suggestion=insights["ai_solution_suggestion"],
            assigned_department=insights["assigned_department"],
            estimated_turnaround=insights["estimated_turnaround"],
            concern_type=insights["concern_type"],
            concern_severity=insights["concern_severity"],
            key_indicators=insights["key_indicators"]
        )
        db.add(new_c)
        db.commit()
        db.refresh(new_c)

        # Check duplicate
        dup_id, sim_score, cluster_tag = find_duplicate_with_details(
            db, new_c.title, new_c.description, cat_str, exclude_id=new_c.id
        )
        if dup_id:
            new_c.duplicate_of_id = dup_id
            new_c.similarity_score = sim_score
            new_c.cluster_tag = cluster_tag
            parent = db.query(models.Complaint).filter(models.Complaint.id == dup_id).first()
            if parent and not parent.cluster_tag:
                parent.cluster_tag = cluster_tag
            db.commit()
        print(f"Created complaint: #{new_c.id} {new_c.title} -> Cluster: {new_c.cluster_tag}")

print("\n--- Summary of All Complaints & Clusters in DB ---")
for c in db.query(models.Complaint).all():
    print(f"#{c.id}: [{c.concern_type}] ({c.priority} Prio) - '{c.title}' | DupOf: #{c.duplicate_of_id} (Sim: {c.similarity_score}%) Cluster: {c.cluster_tag}")

db.close()
