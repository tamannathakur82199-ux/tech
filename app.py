import os
import re
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")
app.config["DATABASE"] = os.path.join(app.root_path, "campuspulse.db")

CATEGORIES = [
    "Infrastructure", "Academics", "Hostel", "Transport",
    "Cleanliness", "IT Services", "Safety & Security", "Other"
]

# Small built-in training set: the app works immediately without downloading a dataset.
TRAINING_DATA = [
    ("broken classroom fan and lights", "Infrastructure"),
    ("damaged desk chair and broken benches", "Infrastructure"),
    ("water leakage in classroom roof", "Infrastructure"),
    ("library building needs repair", "Infrastructure"),
    ("teacher is not taking classes and syllabus is incomplete", "Academics"),
    ("marks are incorrect in internal assessment", "Academics"),
    ("exam date sheet and timetable issue", "Academics"),
    ("need more books and academic support", "Academics"),
    ("hostel room water supply is not working", "Hostel"),
    ("hostel food quality is poor", "Hostel"),
    ("hostel washroom is dirty", "Hostel"),
    ("hostel room allotment problem", "Hostel"),
    ("college bus is late and transport route problem", "Transport"),
    ("bus driver is driving rashly", "Transport"),
    ("need another bus for students", "Transport"),
    ("garbage not collected in campus", "Cleanliness"),
    ("dirty washroom and unhygienic campus", "Cleanliness"),
    ("drinking water area is dirty", "Cleanliness"),
    ("wifi internet is not working", "IT Services"),
    ("computer lab computers are not working", "IT Services"),
    ("unable to access college portal", "IT Services"),
    ("projector and network issue in computer lab", "IT Services"),
    ("broken security gate and no guards", "Safety & Security"),
    ("harassment and threatening behaviour on campus", "Safety & Security"),
    ("emergency medical help required", "Safety & Security"),
    ("general suggestion for college improvement", "Other"),
    ("please organise more cultural activities", "Other"),
]

URGENT_TERMS = [
    "fire", "smoke", "accident", "injury", "injured", "emergency",
    "harassment", "threat", "threatening", "violence", "unsafe",
    "electric shock", "sparking", "exposed wire", "gas leak",
    "medical", "collapsed", "flooding", "severe leak"
]
HIGH_TERMS = [
    "not working", "broken", "no water", "no electricity", "blackout",
    "security", "danger", "urgent", "unsafe", "leakage", "blocked"
]

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(app.config["DATABASE"])
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student','faculty','staff','admin')),
        department TEXT DEFAULT '',
        verified INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        priority TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        duplicate_of INTEGER,
        similarity REAL DEFAULT 0,
        admin_note TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(duplicate_of) REFERENCES complaints(id)
    );
    """)
    # Create a known demo administrator only when no admin exists.
    admin = db.execute("SELECT id FROM users WHERE email = ?", ("admin@campuspulse.local",)).fetchone()
    if not admin:
        db.execute(
            "INSERT INTO users(name,email,password_hash,role,department,verified,created_at) VALUES(?,?,?,?,?,?,?)",
            ("CampusPulse Admin", "admin@campuspulse.local",
             generate_password_hash("Admin@123"), "admin", "Administration", 1,
             datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
    db.commit()
    db.close()

def train_classifier():
    if not SKLEARN_AVAILABLE:
        return None, None
    texts, labels = zip(*TRAINING_DATA)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    matrix = vectorizer.fit_transform(texts)
    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(matrix, labels)
    return vectorizer, model

VECTORIZER, CLASSIFIER = train_classifier()

def classify_text(text):
    if SKLEARN_AVAILABLE and VECTORIZER is not None:
        try:
            prediction = CLASSIFIER.predict(VECTORIZER.transform([text]))[0]
            return prediction
        except Exception:
            pass
    low = text.lower()
    keyword_map = {
        "Infrastructure": ["classroom", "fan", "light", "bench", "building", "repair", "roof"],
        "Academics": ["teacher", "class", "exam", "marks", "syllabus", "lecture", "assignment"],
        "Hostel": ["hostel", "room", "mess", "warden"],
        "Transport": ["bus", "transport", "driver", "route"],
        "Cleanliness": ["garbage", "dirty", "clean", "washroom", "hygiene"],
        "IT Services": ["wifi", "internet", "computer", "portal", "projector", "network"],
        "Safety & Security": ["security", "harassment", "threat", "fire", "accident", "unsafe"]
    }
    scores = {cat: sum(word in low for word in words) for cat, words in keyword_map.items()}
    return max(scores, key=scores.get) if max(scores.values(), default=0) else "Other"

def detect_priority(text):
    low = text.lower()
    if any(term in low for term in URGENT_TERMS):
        return "Urgent"
    if any(term in low for term in HIGH_TERMS):
        return "High"
    return "Medium"

def find_duplicate(text, exclude_id=None):
    if not SKLEARN_AVAILABLE:
        return None, 0.0
    db = get_db()
    rows = db.execute("SELECT id,title,description FROM complaints WHERE duplicate_of IS NULL").fetchall()
    if not rows:
        return None, 0.0
    candidates = [f"{r['title']} {r['description']}" for r in rows]
    try:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        matrix = vectorizer.fit_transform(candidates + [text])
        scores = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
        best_index = int(scores.argmax())
        best_score = float(scores[best_index])
        if best_score >= 0.48:
            return rows[best_index]["id"], best_score
    except ValueError:
        pass
    return None, 0.0

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Administrator access is required.", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_globals():
    return {"current_user": session.get("name"), "current_role": session.get("role")}

@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("admin_dashboard" if session.get("role") == "admin" else "dashboard"))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")
        department = request.form.get("department", "").strip()
        if not name or not email or len(password) < 8 or role not in ("student", "faculty", "staff"):
            flash("Enter all details. Password must contain at least 8 characters.", "danger")
            return render_template("register.html")
        try:
            get_db().execute(
                "INSERT INTO users(name,email,password_hash,role,department,verified,created_at) VALUES(?,?,?,?,?,?,?)",
                (name, email, generate_password_hash(password), role, department, 0,
                 datetime.now().strftime("%Y-%m-%d %H:%M"))
            )
            get_db().commit()
            flash("Registration submitted. An administrator must verify your account before you can log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("This email address is already registered.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            if not user["verified"]:
                flash("Your account is awaiting administrator verification.", "warning")
                return render_template("login.html")
            session.clear()
            session.update(user_id=user["id"], name=user["name"], role=user["role"])
            return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))
    rows = get_db().execute(
        "SELECT * FROM complaints WHERE user_id=? ORDER BY created_at DESC",
        (session["user_id"],)
    ).fetchall()
    return render_template("dashboard.html", complaints=rows)

@app.route("/complaint/new", methods=["GET", "POST"])
@login_required
def new_complaint():
    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        if len(title) < 4 or len(description) < 15:
            flash("Please enter a title (at least 4 characters) and description (at least 15 characters).", "danger")
            return render_template("new_complaint.html")
        combined = f"{title}. {description}"
        category = classify_text(combined)
        priority = detect_priority(combined)
        duplicate_id, similarity = find_duplicate(combined)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cur = get_db().execute(
            """INSERT INTO complaints(user_id,title,description,category,priority,status,duplicate_of,similarity,created_at,updated_at)
               VALUES(?,?,?,?,?,'Pending',?,?,?,?)""",
            (session["user_id"], title, description, category, priority,
             duplicate_id, similarity, now, now)
        )
        get_db().commit()
        if duplicate_id:
            flash(f"Submitted. This appears related to complaint #{duplicate_id} ({similarity:.0%} text similarity); an administrator will review it.", "warning")
        else:
            flash(f"Complaint submitted and automatically classified as {category} with {priority} priority.", "success")
        return redirect(url_for("dashboard"))
    return render_template("new_complaint.html")

@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    total = db.execute("SELECT COUNT(*) n FROM complaints").fetchone()["n"]
    pending = db.execute("SELECT COUNT(*) n FROM complaints WHERE status='Pending'").fetchone()["n"]
    urgent = db.execute("SELECT COUNT(*) n FROM complaints WHERE priority='Urgent'").fetchone()["n"]
    resolved = db.execute("SELECT COUNT(*) n FROM complaints WHERE status='Resolved'").fetchone()["n"]
    categories = db.execute("SELECT category,COUNT(*) count FROM complaints GROUP BY category ORDER BY count DESC").fetchall()
    priority_counts = db.execute("SELECT priority,COUNT(*) count FROM complaints GROUP BY priority").fetchall()
    complaints = db.execute("""
        SELECT c.*,u.name,u.email,u.role
        FROM complaints c JOIN users u ON c.user_id=u.id
        ORDER BY CASE c.priority WHEN 'Urgent' THEN 1 WHEN 'High' THEN 2 ELSE 3 END,
                 CASE c.status WHEN 'Pending' THEN 1 WHEN 'In Progress' THEN 2 ELSE 3 END,
                 c.created_at DESC
    """).fetchall()
    users = db.execute("SELECT * FROM users WHERE role!='admin' ORDER BY verified ASC, created_at DESC").fetchall()
    duplicate_count = db.execute("SELECT COUNT(*) n FROM complaints WHERE duplicate_of IS NOT NULL").fetchone()["n"]
    return render_template("admin.html", total=total, pending=pending, urgent=urgent,
                           resolved=resolved, categories=categories, priority_counts=priority_counts,
                           complaints=complaints, users=users, duplicate_count=duplicate_count)

@app.route("/admin/user/<int:user_id>/verify", methods=["POST"])
@admin_required
def verify_user(user_id):
    get_db().execute("UPDATE users SET verified=1 WHERE id=? AND role!='admin'", (user_id,))
    get_db().commit()
    flash("User account verified.", "success")
    return redirect(url_for("admin_dashboard") + "#users")

@app.route("/admin/complaint/<int:complaint_id>/update", methods=["POST"])
@admin_required
def update_complaint(complaint_id):
    status = request.form.get("status")
    note = request.form.get("admin_note", "").strip()
    if status not in ("Pending", "In Progress", "Resolved", "Rejected"):
        flash("Invalid status.", "danger")
        return redirect(url_for("admin_dashboard"))
    get_db().execute(
        "UPDATE complaints SET status=?,admin_note=?,updated_at=? WHERE id=?",
        (status, note, datetime.now().strftime("%Y-%m-%d %H:%M"), complaint_id)
    )
    get_db().commit()
    flash(f"Complaint #{complaint_id} updated.", "success")
    return redirect(url_for("admin_dashboard") + "#complaints")

@app.route("/complaint/<int:complaint_id>")
@login_required
def complaint_detail(complaint_id):
    complaint = get_db().execute("""
        SELECT c.*,u.name,u.role FROM complaints c JOIN users u ON c.user_id=u.id WHERE c.id=?
    """, (complaint_id,)).fetchone()
    if not complaint:
        flash("Complaint not found.", "danger")
        return redirect(url_for("dashboard"))
    if session.get("role") != "admin" and complaint["user_id"] != session["user_id"]:
        flash("You cannot view this complaint.", "danger")
        return redirect(url_for("dashboard"))
    duplicate = None
    if complaint["duplicate_of"]:
        duplicate = get_db().execute("SELECT id,title,status FROM complaints WHERE id=?", (complaint["duplicate_of"],)).fetchone()
    related = get_db().execute("SELECT id,title,status,similarity FROM complaints WHERE duplicate_of=? ORDER BY created_at DESC", (complaint_id,)).fetchall()
    return render_template("detail.html", complaint=complaint, duplicate=duplicate, related=related)

@app.route("/health")
def health():
    return {"status": "ok", "classifier": "scikit-learn" if SKLEARN_AVAILABLE else "keyword fallback"}

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
