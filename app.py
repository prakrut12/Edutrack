from datetime import date, timedelta
from functools import wraps
import os
import sqlite3

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "edutrack-dev-secret-change-me")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'teacher',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            class_name TEXT NOT NULL,
            section TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            code TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Present', 'Absent')),
            marked_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, subject_id, attendance_date),
            FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE,
            FOREIGN KEY (marked_by) REFERENCES users (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            exam_name TEXT NOT NULL,
            marks_obtained REAL NOT NULL,
            max_marks REAL NOT NULL,
            marked_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, subject_id, exam_name),
            FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE,
            FOREIGN KEY (marked_by) REFERENCES users (id) ON DELETE CASCADE
        );
        """
    )
    seed_data(db)
    db.commit()


def seed_data(db):
    if db.execute("SELECT id FROM users WHERE username = ?", ("teacher",)).fetchone() is None:
        db.execute(
            "INSERT INTO users (username, password, full_name, role) VALUES (?, ?, ?, ?)",
            ("teacher", generate_password_hash("teacher123"), "Ananya Teacher", "teacher"),
        )

    subjects = [
        ("Python Programming", "PY101"),
        ("Database Management", "DB201"),
        ("Web Technologies", "WT301"),
        ("Data Structures", "DS102"),
    ]
    for name, code in subjects:
        if db.execute("SELECT id FROM subjects WHERE code = ?", (code,)).fetchone() is None:
            db.execute("INSERT INTO subjects (name, code) VALUES (?, ?)", (name, code))

    students = [
        ("CS001", "Prakruthi S", "prakruthi@example.edu", "CSE 3rd Year", "A"),
        ("CS002", "Nisha Rao", "nisha@example.edu", "CSE 3rd Year", "A"),
        ("CS003", "Rahul K", "rahul@example.edu", "CSE 3rd Year", "A"),
        ("CS004", "Meghana P", "meghana@example.edu", "CSE 3rd Year", "B"),
        ("CS005", "Arjun M", "arjun@example.edu", "CSE 3rd Year", "B"),
    ]
    for roll_no, full_name, email, class_name, section in students:
        if db.execute("SELECT id FROM students WHERE roll_no = ?", (roll_no,)).fetchone() is None:
            db.execute(
                """
                INSERT INTO students (roll_no, full_name, email, class_name, section)
                VALUES (?, ?, ?, ?, ?)
                """,
                (roll_no, full_name, email, class_name, section),
            )

    total_attendance = db.execute("SELECT COUNT(*) AS total FROM attendance").fetchone()["total"]
    if total_attendance == 0:
        teacher = db.execute("SELECT id FROM users WHERE username = ?", ("teacher",)).fetchone()
        all_students = db.execute("SELECT id FROM students ORDER BY id").fetchall()
        all_subjects = db.execute("SELECT id FROM subjects ORDER BY id").fetchall()
        today = date.today()
        for day_offset in range(10):
            current = (today - timedelta(days=day_offset)).isoformat()
            for subject in all_subjects:
                for index, student in enumerate(all_students):
                    status = "Absent" if (index + day_offset + subject["id"]) % 7 == 0 else "Present"
                    db.execute(
                        """
                        INSERT OR IGNORE INTO attendance
                        (student_id, subject_id, attendance_date, status, marked_by)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (student["id"], subject["id"], current, status, teacher["id"]),
                    )

    total_marks = db.execute("SELECT COUNT(*) AS total FROM marks").fetchone()["total"]
    if total_marks == 0:
        teacher = db.execute("SELECT id FROM users WHERE username = ?", ("teacher",)).fetchone()
        all_students = db.execute("SELECT id FROM students ORDER BY id").fetchall()
        all_subjects = db.execute("SELECT id FROM subjects ORDER BY id").fetchall()
        exams = ["Internal 1", "Internal 2"]
        for exam_index, exam_name in enumerate(exams):
            for subject in all_subjects:
                for index, student in enumerate(all_students):
                    score = 32 + ((index * 7 + subject["id"] * 5 + exam_index * 4) % 18)
                    db.execute(
                        """
                        INSERT OR IGNORE INTO marks
                        (student_id, subject_id, exam_name, marks_obtained, max_marks, marked_by)
                        VALUES (?, ?, ?, ?, 50, ?)
                        """,
                        (student["id"], subject["id"], exam_name, score, teacher["id"]),
                    )


@app.before_request
def load_user():
    user_id = session.get("user_id")
    g.user = None
    if user_id:
        g.user = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def login_required(view):
    @wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped


@app.route("/")
def index():
    if g.user:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user is None or not check_password_hash(user["password"], password):
            flash("Invalid username or password.", "danger")
        else:
            session.clear()
            session["user_id"] = user["id"]
            flash("Welcome to EduTrack.", "success")
            return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    summary = {
        "students": db.execute("SELECT COUNT(*) AS total FROM students").fetchone()["total"],
        "subjects": db.execute("SELECT COUNT(*) AS total FROM subjects").fetchone()["total"],
        "attendance": db.execute("SELECT COUNT(*) AS total FROM attendance").fetchone()["total"],
        "marks": db.execute("SELECT COUNT(*) AS total FROM marks").fetchone()["total"],
    }
    low_attendance = low_attendance_rows(db, limit=5)
    subject_report = subject_report_rows(db)
    return render_template(
        "dashboard.html",
        summary=summary,
        low_attendance=low_attendance,
        subject_report=subject_report,
    )


@app.route("/students")
@login_required
def students():
    q = request.args.get("q", "").strip()
    db = get_db()
    query = "SELECT * FROM students WHERE 1 = 1"
    params = []
    if q:
        query += " AND (full_name LIKE ? OR roll_no LIKE ? OR class_name LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    query += " ORDER BY roll_no"
    rows = db.execute(query, params).fetchall()
    return render_template("students.html", students=rows, q=q)


@app.route("/students/new", methods=("GET", "POST"))
@login_required
def add_student():
    if request.method == "POST":
        db = get_db()
        try:
            db.execute(
                """
                INSERT INTO students (roll_no, full_name, email, class_name, section)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    request.form["roll_no"].strip(),
                    request.form["full_name"].strip(),
                    request.form["email"].strip(),
                    request.form["class_name"].strip(),
                    request.form["section"].strip(),
                ),
            )
            db.commit()
            flash("Student added successfully.", "success")
            return redirect(url_for("students"))
        except sqlite3.IntegrityError:
            flash("A student with that roll number already exists.", "danger")
    return render_template("student_form.html")


@app.route("/attendance", methods=("GET", "POST"))
@login_required
def attendance():
    db = get_db()
    subjects = db.execute("SELECT * FROM subjects ORDER BY name").fetchall()
    selected_subject = request.values.get("subject_id") or (subjects[0]["id"] if subjects else None)
    selected_date = request.values.get("attendance_date") or date.today().isoformat()
    students = db.execute("SELECT * FROM students ORDER BY roll_no").fetchall()

    if request.method == "POST":
        for student in students:
            status = request.form.get(f"student_{student['id']}", "Absent")
            db.execute(
                """
                INSERT INTO attendance (student_id, subject_id, attendance_date, status, marked_by)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(student_id, subject_id, attendance_date)
                DO UPDATE SET status = excluded.status, marked_by = excluded.marked_by
                """,
                (student["id"], selected_subject, selected_date, status, g.user["id"]),
            )
        db.commit()
        flash("Attendance saved.", "success")
        return redirect(url_for("attendance", subject_id=selected_subject, attendance_date=selected_date))

    existing = db.execute(
        """
        SELECT student_id, status FROM attendance
        WHERE subject_id = ? AND attendance_date = ?
        """,
        (selected_subject, selected_date),
    ).fetchall()
    attendance_map = {row["student_id"]: row["status"] for row in existing}
    return render_template(
        "attendance.html",
        subjects=subjects,
        students=students,
        selected_subject=str(selected_subject),
        selected_date=selected_date,
        attendance_map=attendance_map,
    )


@app.route("/marks", methods=("GET", "POST"))
@login_required
def marks():
    db = get_db()
    subjects = db.execute("SELECT * FROM subjects ORDER BY name").fetchall()
    students = db.execute("SELECT * FROM students ORDER BY roll_no").fetchall()
    selected_subject = request.values.get("subject_id") or (subjects[0]["id"] if subjects else None)
    exam_name = request.values.get("exam_name") or "Internal 1"
    max_marks = float(request.values.get("max_marks") or 50)

    if request.method == "POST":
        for student in students:
            value = request.form.get(f"student_{student['id']}", "").strip()
            if value:
                db.execute(
                    """
                    INSERT INTO marks (student_id, subject_id, exam_name, marks_obtained, max_marks, marked_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(student_id, subject_id, exam_name)
                    DO UPDATE SET marks_obtained = excluded.marks_obtained,
                                  max_marks = excluded.max_marks,
                                  marked_by = excluded.marked_by
                    """,
                    (student["id"], selected_subject, exam_name, float(value), max_marks, g.user["id"]),
                )
        db.commit()
        flash("Marks saved.", "success")
        return redirect(url_for("marks", subject_id=selected_subject, exam_name=exam_name, max_marks=max_marks))

    existing = db.execute(
        """
        SELECT student_id, marks_obtained FROM marks
        WHERE subject_id = ? AND exam_name = ?
        """,
        (selected_subject, exam_name),
    ).fetchall()
    marks_map = {row["student_id"]: row["marks_obtained"] for row in existing}
    return render_template(
        "marks.html",
        subjects=subjects,
        students=students,
        selected_subject=str(selected_subject),
        exam_name=exam_name,
        max_marks=max_marks,
        marks_map=marks_map,
    )


@app.route("/low-attendance")
@login_required
def low_attendance():
    threshold = float(request.args.get("threshold") or 75)
    rows = low_attendance_rows(get_db(), threshold=threshold)
    return render_template("low_attendance.html", rows=rows, threshold=threshold)


@app.route("/reports")
@login_required
def reports():
    db = get_db()
    subject_report = subject_report_rows(db)
    toppers = db.execute(
        """
        SELECT students.roll_no, students.full_name,
               ROUND(AVG((marks.marks_obtained / marks.max_marks) * 100), 2) AS average_percent
        FROM marks
        JOIN students ON students.id = marks.student_id
        GROUP BY students.id
        ORDER BY average_percent DESC
        LIMIT 8
        """
    ).fetchall()
    return render_template("reports.html", subject_report=subject_report, toppers=toppers)


def low_attendance_rows(db, threshold=75, limit=None):
    query = """
        SELECT students.roll_no, students.full_name, subjects.name AS subject_name,
               COUNT(attendance.id) AS total_classes,
               SUM(CASE WHEN attendance.status = 'Present' THEN 1 ELSE 0 END) AS present_count,
               ROUND((SUM(CASE WHEN attendance.status = 'Present' THEN 1 ELSE 0 END) * 100.0)
                     / COUNT(attendance.id), 2) AS percentage
        FROM attendance
        JOIN students ON students.id = attendance.student_id
        JOIN subjects ON subjects.id = attendance.subject_id
        GROUP BY students.id, subjects.id
        HAVING percentage < ?
        ORDER BY percentage ASC
    """
    params = [threshold]
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    return db.execute(query, params).fetchall()


def subject_report_rows(db):
    return db.execute(
        """
        SELECT subjects.name AS subject_name,
               COUNT(DISTINCT attendance.attendance_date) AS classes_marked,
               ROUND(AVG(CASE WHEN attendance.status = 'Present' THEN 100 ELSE 0 END), 2) AS attendance_percent,
               ROUND(AVG((marks.marks_obtained / marks.max_marks) * 100), 2) AS marks_percent
        FROM subjects
        LEFT JOIN attendance ON attendance.subject_id = subjects.id
        LEFT JOIN marks ON marks.subject_id = subjects.id
        GROUP BY subjects.id
        ORDER BY subjects.name
        """
    ).fetchall()


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True, port=5003)
