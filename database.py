import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./complaints.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Safe auto-migration and admin account guarantee
def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN admin_id VARCHAR;"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE complaints ADD COLUMN submission_type VARCHAR DEFAULT 'Complaint';"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE complaints ADD COLUMN ai_analysis TEXT;"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE complaints ADD COLUMN ai_solution_suggestion TEXT;"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE complaints ADD COLUMN assigned_department VARCHAR DEFAULT 'Campus Estates & Facilities';"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE complaints ADD COLUMN estimated_turnaround VARCHAR DEFAULT '24-48 Hours';"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE complaints ADD COLUMN concern_type VARCHAR DEFAULT 'General Campus Maintenance';"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE complaints ADD COLUMN concern_severity VARCHAR DEFAULT 'Moderate';"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE complaints ADD COLUMN key_indicators VARCHAR;"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE complaints ADD COLUMN cluster_tag VARCHAR;"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE complaints ADD COLUMN similarity_score INTEGER DEFAULT 0;"))
            conn.commit()
        except Exception:
            pass

        try:
            from .utils.security import get_password_hash
            hashed = get_password_hash("adminpass")
            conn.execute(text("UPDATE users SET role = 'admin', admin_id = 'ADM-001', is_verified = 1 WHERE email = 'admin@college.edu';"))
            conn.commit()
            check = conn.execute(text("SELECT id FROM users WHERE email = 'admin@college.edu' OR admin_id = 'ADM-001';")).first()
            if not check:
                conn.execute(text(f"INSERT INTO users (email, admin_id, hashed_password, is_verified, role, created_at) VALUES ('admin@college.edu', 'ADM-001', '{hashed}', 1, 'admin', CURRENT_TIMESTAMP);"))
                conn.commit()
        except Exception:
            pass
