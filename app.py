"""LearnMind - AI-powered student learning companion.

The existing SQLite database is kept in place and upgraded safely on startup.
Never commit .env, database.db, or your virtual environment to source control.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import (
    Flask, abort, flash, g, jsonify, redirect, render_template,
    request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("FLASK_SECRET_KEY") or secrets.token_urlsafe(32),
    DATABASE=os.getenv("LEARNMIND_DATABASE", str(BASE_DIR / "database.db")),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "0") == "1",
    MAX_CONTENT_LENGTH=1 * 1024 * 1024,
)
app.logger.setLevel(logging.INFO)

DEFAULT_SUBJECTS = [
    "Natural Language Processing",
    "Digital Image Processing",
    "Neural Networks",
    "Quantitative Techniques",
]

# Questions are kept on the server so students cannot change the answer key
# through browser developer tools before submitting a quiz.
QUIZ_BANK: dict[str, list[dict[str, Any]]] = {
    "Natural Language Processing": [
        {"topic": "NLP Basics", "question": "What is the full form of NLP?", "options": ["Natural Language Processing", "Network Learning Program", "Neural Logic Processing", "Natural Learning Program"], "answer": 0, "explanation": "NLP enables computers to work with human language."},
        {"topic": "Tokenization", "question": "What is tokenization?", "options": ["Deleting a document", "Breaking text into smaller units", "Translating images", "Creating a database"], "answer": 1, "explanation": "Tokenization splits text into tokens such as words or subwords."},
        {"topic": "Stop Words", "question": "Which is commonly considered a stop word?", "options": ["Computer", "Learning", "The", "Technology"], "answer": 2, "explanation": "Common words such as 'the' are often filtered in basic NLP tasks."},
        {"topic": "Stemming", "question": "What is the purpose of stemming?", "options": ["Finding a root-like word form", "Increasing image size", "Sorting a database", "Creating a webpage"], "answer": 0, "explanation": "Stemming reduces related word forms to a common stem."},
        {"topic": "Sentiment Analysis", "question": "Sentiment analysis identifies:", "options": ["File size", "Text sentiment or opinion", "Screen resolution", "Network speed"], "answer": 1, "explanation": "Sentiment analysis classifies opinions as positive, negative, or neutral."},
    ],
    "Digital Image Processing": [
        {"topic": "Image Basics", "question": "What is a digital image made up of?", "options": ["Pixels", "Paragraphs", "Tables", "Functions only"], "answer": 0, "explanation": "A digital image is represented as a grid of pixels."},
        {"topic": "Image Filtering", "question": "Which operation can reduce image noise?", "options": ["Filtering", "Typing", "Compiling", "Sorting text"], "answer": 0, "explanation": "Filters such as median and Gaussian filters can reduce noise."},
        {"topic": "Segmentation", "question": "What is image segmentation?", "options": ["Dividing an image into meaningful regions", "Printing an image", "Renaming an image", "Deleting an image"], "answer": 0, "explanation": "Segmentation separates an image into regions or objects."},
        {"topic": "Resolution", "question": "Image resolution is commonly related to:", "options": ["Number of pixels", "Number of paragraphs", "Keyboard speed", "Internet history"], "answer": 0, "explanation": "Pixel dimensions determine the spatial resolution of a raster image."},
        {"topic": "Grayscale", "question": "A standard 8-bit grayscale image can represent how many intensity levels?", "options": ["8", "16", "128", "256"], "answer": 3, "explanation": "Eight bits represent 2^8, or 256, possible intensity values."},
    ],
    "Neural Networks": [
        {"topic": "Neural Network Basics", "question": "Artificial neural networks are loosely inspired by:", "options": ["The human brain", "Printers", "Keyboards", "Databases"], "answer": 0, "explanation": "Artificial neural networks take inspiration from connected biological neurons."},
        {"topic": "Neuron", "question": "What does an artificial neuron receive as input?", "options": ["Signals or input values", "Only images", "Only passwords", "Only output files"], "answer": 0, "explanation": "A neuron receives input values, applies weights and a bias, then activates."},
        {"topic": "Activation Functions", "question": "What is the purpose of an activation function?", "options": ["Introduce non-linearity", "Delete the network", "Store files", "Format a document"], "answer": 0, "explanation": "Activation functions allow networks to learn non-linear relationships."},
        {"topic": "Perceptron", "question": "A perceptron is a basic model of:", "options": ["An artificial neuron", "A web browser", "A database table", "An operating system"], "answer": 0, "explanation": "A perceptron is a simple computational model of a neuron."},
        {"topic": "Network Layers", "question": "Which layer is between input and output layers in a typical multilayer network?", "options": ["Hidden layer", "Storage layer", "Printing layer", "Display layer"], "answer": 0, "explanation": "Hidden layers process inputs between the input and output layers."},
    ],
    "Quantitative Techniques": [
        {"topic": "Mean", "question": "Find the mean of 2, 4, 6 and 8.", "options": ["4", "5", "6", "8"], "answer": 1, "explanation": "Mean = (2 + 4 + 6 + 8) / 4 = 5."},
        {"topic": "Median", "question": "What is the median of 3, 7, 9?", "options": ["3", "7", "9", "19"], "answer": 1, "explanation": "The median is the middle value after sorting the data."},
        {"topic": "Mode", "question": "What is the mode of 2, 3, 3, 4, 5?", "options": ["2", "3", "4", "5"], "answer": 1, "explanation": "The mode is the value that occurs most frequently."},
        {"topic": "Probability", "question": "What is the probability of getting a head on a fair coin toss?", "options": ["0", "1/4", "1/2", "1"], "answer": 2, "explanation": "There are two equally likely outcomes, so P(head) = 1/2."},
        {"topic": "Range", "question": "Find the range of 5, 9, 12, 18.", "options": ["9", "12", "13", "18"], "answer": 2, "explanation": "Range = maximum − minimum = 18 − 5 = 13."},
    ],
    "Python Programming": [
        {"topic": "Python Basics", "question": "Which keyword is used to define a function in Python?", "options": ["function", "def", "define", "fun"], "answer": 1, "explanation": "Python functions are declared with the def keyword."},
        {"topic": "Variables", "question": "Which is a valid Python variable assignment?", "options": ["x = 10", "int x := 10", "10 = x", "x == assign 10"], "answer": 0, "explanation": "Python assigns a value using the = operator."},
        {"topic": "Data Types", "question": "Which data type stores True or False?", "options": ["str", "list", "bool", "dict"], "answer": 2, "explanation": "The bool type stores Boolean values True and False."},
        {"topic": "Loops", "question": "Which loop is commonly used to iterate over items in a list?", "options": ["for", "switch", "case", "repeat-until"], "answer": 0, "explanation": "A for loop iterates through each item in an iterable."},
        {"topic": "Collections", "question": "Which Python collection is ordered and changeable?", "options": ["tuple", "list", "frozenset", "None"], "answer": 1, "explanation": "Lists maintain order and can be modified."},
    ],
}


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = Path(app.config["DATABASE"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 15000")
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_error: BaseException | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db() -> None:
    """Create new tables and upgrade existing LearnMind databases in place."""
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0 CHECK(progress BETWEEN 0 AND 100),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                score INTEGER NOT NULL,
                total INTEGER NOT NULL,
                percentage REAL NOT NULL,
                details_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_subjects_user ON subjects(user_id);
            CREATE INDEX IF NOT EXISTS idx_quiz_user_date ON quiz_attempts(user_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_chat_user_date ON chat_messages(user_id, created_at);
        """)

        # Upgrade legacy databases: secure plain-text passwords without losing accounts.
        users = conn.execute("SELECT id, password FROM users").fetchall()
        for user in users:
            current = user["password"] or ""
            if not current.startswith(("scrypt:", "pbkdf2:")):
                conn.execute(
                    "UPDATE users SET password = ? WHERE id = ?",
                    (generate_password_hash(current), user["id"]),
                )

        # Ensure every existing account has the four original LearnMind subjects.
        existing_users = conn.execute("SELECT id FROM users").fetchall()
        for user in existing_users:
            for subject_name in DEFAULT_SUBJECTS:
                exists = conn.execute(
                    "SELECT 1 FROM subjects WHERE user_id = ? AND lower(name) = lower(?) LIMIT 1",
                    (user["id"], subject_name),
                ).fetchone()
                if not exists:
                    conn.execute(
                        "INSERT INTO subjects(user_id, name, progress) VALUES (?, ?, 0)",
                        (user["id"], subject_name),
                    )
        conn.commit()
    finally:
        conn.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/") or request.path == "/ask_ai":
                return jsonify({"error": "Please log in to continue."}), 401
            return redirect(url_for("login", next=request.full_path if request.query_string else request.path))
        return view(*args, **kwargs)
    return wrapped


def csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


@app.context_processor
def inject_template_helpers():
    return {"csrf_token": csrf_token, "current_user": session.get("user_name", "Student")}


@app.before_request
def protect_post_requests():
    if request.method == "POST":
        supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        expected = session.get("csrf_token", "")
        if not supplied or not expected or not secrets.compare_digest(supplied, expected):
            if request.path.startswith("/api/") or request.path == "/ask_ai":
                return jsonify({"error": "Your session token expired. Refresh the page and try again."}), 400
            abort(400, description="Your form session expired. Please go back, refresh the page and try again.")


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response


def user_subjects(user_id: int):
    return get_db().execute(
        "SELECT id, name, progress FROM subjects WHERE user_id = ? ORDER BY name COLLATE NOCASE",
        (user_id,),
    ).fetchall()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@app.get("/")
def landing():
    if "user_id" in session:
        return redirect(url_for("home"))
    return render_template("landing.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if not name or len(name) > 80 or not email or len(email) > 254 or not password:
        flash("Please complete all fields with valid values.", "error")
        return render_template("signup.html", name=name, email=email), 400
    if len(password) < 8:
        flash("Use a password with at least 8 characters.", "error")
        return render_template("signup.html", name=name, email=email), 400

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO users(name, email, password) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        user_id = cur.lastrowid
        for subject_name in DEFAULT_SUBJECTS:
            db.execute(
                "INSERT INTO subjects(user_id, name, progress) VALUES (?, ?, 0)",
                (user_id, subject_name),
            )
        db.commit()
    except sqlite3.IntegrityError:
        flash("This email address is already registered. Please log in.", "error")
        return render_template("signup.html", name=name, email=email), 409

    session.clear()
    session["user_id"] = user_id
    session["user_name"] = name
    csrf_token()
    flash("Your LearnMind account is ready. Welcome!", "success")
    return redirect(url_for("home"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = get_db().execute(
        "SELECT id, name, password FROM users WHERE lower(email) = lower(?)",
        (email,),
    ).fetchone()
    if not user or not check_password_hash(user["password"], password):
        flash("Invalid email or password. Please try again.", "error")
        return render_template("login.html", email=email), 401

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    csrf_token()
    flash(f"Welcome back, {user['name']}!", "success")
    next_url = request.args.get("next", "")
    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect(url_for("home"))


@app.post("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("landing"))


@app.get("/home")
@login_required
def home():
    user_id = session["user_id"]
    db = get_db()
    subjects = user_subjects(user_id)
    subject_count = len(subjects)
    overall_progress = round(sum(row["progress"] for row in subjects) / subject_count) if subject_count else 0
    today = datetime.now().astimezone().date().isoformat()
    week_start = (datetime.now().astimezone() - timedelta(days=6)).date().isoformat()
    today_count = db.execute(
        "SELECT COUNT(*) FROM quiz_attempts WHERE user_id = ? AND substr(created_at, 1, 10) = ?",
        (user_id, today),
    ).fetchone()[0]
    weekly_count = db.execute(
        "SELECT COUNT(*) FROM quiz_attempts WHERE user_id = ? AND substr(created_at, 1, 10) >= ?",
        (user_id, week_start),
    ).fetchone()[0]
    recent_attempts = db.execute(
        "SELECT subject, score, total, percentage, created_at FROM quiz_attempts WHERE user_id = ? ORDER BY id DESC LIMIT 5",
        (user_id,),
    ).fetchall()
    return render_template(
        "home.html", subjects=subjects, subject_count=subject_count,
        overall_progress=overall_progress, today_count=today_count,
        weekly_count=weekly_count, weekly_goal=7, recent_attempts=recent_attempts,
    )


@app.get("/my-learning")
@login_required
def my_learning():
    return render_template("my_learning.html", subjects=user_subjects(session["user_id"]))


@app.post("/subjects/add")
@login_required
def add_subject():
    name = request.form.get("subject_name", "").strip()
    if not name or len(name) > 80:
        flash("Enter a subject name (up to 80 characters).", "error")
        return redirect(url_for("my_learning"))
    db = get_db()
    duplicate = db.execute(
        "SELECT 1 FROM subjects WHERE user_id = ? AND lower(name) = lower(?)",
        (session["user_id"], name),
    ).fetchone()
    if duplicate:
        flash("That subject is already in your learning list.", "error")
    else:
        db.execute("INSERT INTO subjects(user_id, name, progress) VALUES (?, ?, 0)", (session["user_id"], name))
        db.commit()
        flash(f"{name} was added to My Learning.", "success")
    return redirect(url_for("my_learning"))


@app.post("/subjects/<int:subject_id>/update")
@login_required
def update_subject(subject_id: int):
    name = request.form.get("name", "").strip()
    try:
        progress = int(request.form.get("progress", "0"))
    except ValueError:
        progress = -1
    if not name or len(name) > 80 or not 0 <= progress <= 100:
        flash("Enter a valid subject name and progress from 0 to 100.", "error")
        return redirect(url_for("my_learning"))
    db = get_db()
    result = db.execute(
        "UPDATE subjects SET name = ?, progress = ? WHERE id = ? AND user_id = ?",
        (name, progress, subject_id, session["user_id"]),
    )
    db.commit()
    flash("Subject updated." if result.rowcount else "Subject not found.", "success" if result.rowcount else "error")
    return redirect(url_for("my_learning"))


@app.post("/subjects/<int:subject_id>/delete")
@login_required
def delete_subject(subject_id: int):
    db = get_db()
    result = db.execute("DELETE FROM subjects WHERE id = ? AND user_id = ?", (subject_id, session["user_id"]))
    db.commit()
    flash("Subject removed from My Learning." if result.rowcount else "Subject not found.", "success" if result.rowcount else "error")
    return redirect(url_for("my_learning"))


@app.get("/ai-assistant")
@login_required
def ai_assistant():
    return render_template("ai_assistant.html")


@app.get("/study-debugger")
@login_required
def study_debugger():
    available_names = {row["name"] for row in user_subjects(session["user_id"])}
    subjects = [name for name in QUIZ_BANK if name in available_names]
    return render_template("study_debugger.html", quiz_subjects=subjects)


@app.get("/api/quiz/questions")
@login_required
def quiz_questions():
    subject = request.args.get("subject", "")
    if subject not in QUIZ_BANK:
        return jsonify({"error": "No quiz is available for this subject yet."}), 404
    safe_questions = [
        {"topic": q["topic"], "question": q["question"], "options": q["options"]}
        for q in QUIZ_BANK[subject]
    ]
    return jsonify({"subject": subject, "questions": safe_questions})


@app.post("/api/quiz/submit")
@login_required
def submit_quiz():
    data = request.get_json(silent=True) or {}
    subject = data.get("subject")
    answers = data.get("answers")
    if subject not in QUIZ_BANK or not isinstance(answers, list):
        return jsonify({"error": "Invalid quiz submission."}), 400
    questions = QUIZ_BANK[subject]
    if len(answers) != len(questions):
        return jsonify({"error": "Please answer every question before submitting."}), 400

    details = []
    score = 0
    for question, selected in zip(questions, answers):
        try:
            selected_index = int(selected)
        except (ValueError, TypeError):
            return jsonify({"error": "One or more answers are invalid."}), 400
        if not 0 <= selected_index < len(question["options"]):
            return jsonify({"error": "One or more answers are invalid."}), 400
        correct = selected_index == question["answer"]
        score += int(correct)
        details.append({
            "topic": question["topic"],
            "correct": correct,
            "selected": question["options"][selected_index],
            "correct_answer": question["options"][question["answer"]],
            "explanation": question["explanation"],
        })
    percentage = round(score / len(questions) * 100, 1)
    db = get_db()
    db.execute(
        "INSERT INTO quiz_attempts(user_id, subject, score, total, percentage, details_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (session["user_id"], subject, score, len(questions), percentage, json.dumps(details), now_iso()),
    )
    # Keep the subject's displayed progress aligned with the student's latest quiz result.
    db.execute(
        "UPDATE subjects SET progress = ? WHERE user_id = ? AND lower(name) = lower(?)",
        (round(percentage), session["user_id"], subject),
    )
    db.commit()
    weak_topics = [item["topic"] for item in details if not item["correct"]]
    return jsonify({
        "score": score, "total": len(questions), "percentage": percentage,
        "details": details, "weak_topics": weak_topics,
        "message": "Excellent work! Keep challenging yourself." if percentage >= 80 else "Good effort. Review the suggested topics and try again.",
    })


@app.get("/progress")
@login_required
def progress():
    db = get_db()
    user_id = session["user_id"]
    subjects = user_subjects(user_id)
    attempts = db.execute(
        "SELECT subject, score, total, percentage, created_at FROM quiz_attempts WHERE user_id = ? ORDER BY id DESC LIMIT 30",
        (user_id,),
    ).fetchall()
    subject_stats = db.execute(
        "SELECT subject, COUNT(*) AS attempts, ROUND(AVG(percentage), 1) AS average, MAX(percentage) AS best FROM quiz_attempts WHERE user_id = ? GROUP BY subject ORDER BY subject",
        (user_id,),
    ).fetchall()
    total_attempts = db.execute("SELECT COUNT(*) FROM quiz_attempts WHERE user_id = ?", (user_id,)).fetchone()[0]
    average_score = db.execute("SELECT ROUND(AVG(percentage), 1) FROM quiz_attempts WHERE user_id = ?", (user_id,)).fetchone()[0] or 0
    return render_template(
        "progress.html", subjects=subjects, attempts=attempts,
        subject_stats=subject_stats, total_attempts=total_attempts,
        average_score=average_score,
    )


@app.get("/resources")
@login_required
def resources():
    return render_template("resources.html")


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    db = get_db()
    user = db.execute("SELECT id, name, email, password FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if request.method == "POST":
        action = request.form.get("action", "profile")
        if action == "profile":
            name = request.form.get("name", "").strip()
            if not name or len(name) > 80:
                flash("Your name must be between 1 and 80 characters.", "error")
            else:
                db.execute("UPDATE users SET name = ? WHERE id = ?", (name, session["user_id"]))
                db.commit()
                session["user_name"] = name
                flash("Profile updated successfully.", "success")
        elif action == "password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            if not check_password_hash(user["password"], current_password):
                flash("Your current password is incorrect.", "error")
            elif len(new_password) < 8:
                flash("Your new password must contain at least 8 characters.", "error")
            else:
                db.execute("UPDATE users SET password = ? WHERE id = ?", (generate_password_hash(new_password), session["user_id"]))
                db.commit()
                flash("Password changed successfully.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", user=user)


class GeminiTemporarilyUnavailable(RuntimeError):
    """Raised when all configured Gemini models are temporarily unavailable."""


TRANSIENT_GEMINI_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def _gemini_error_code(error: Exception) -> int | None:
    """Return the HTTP status from a google-genai APIError, if present."""
    code = getattr(error, "code", None)
    try:
        return int(code) if code is not None else None
    except (TypeError, ValueError):
        return None


def _generate_with_model_fallback(client: Any, models: list[str], prompt: str) -> str:
    """Try the primary model, then the configured fallback on transient API errors."""
    last_transient_error: Exception | None = None

    for index, model in enumerate(models):
        try:
            response = client.models.generate_content(model=model, contents=prompt)
        except Exception as exc:
            status_code = _gemini_error_code(exc)
            if status_code in TRANSIENT_GEMINI_STATUS_CODES:
                last_transient_error = exc
                if index < len(models) - 1:
                    app.logger.warning(
                        "Gemini model %s returned HTTP %s; trying fallback model %s.",
                        model, status_code, models[index + 1],
                    )
                    continue
                break
            # A missing primary model can also be recovered by trying the fallback.
            if status_code == 404 and index < len(models) - 1:
                app.logger.warning(
                    "Gemini model %s was not found; trying fallback model %s.",
                    model, models[index + 1],
                )
                continue
            raise

        answer = (getattr(response, "text", None) or "").strip()
        if not answer:
            raise RuntimeError(f"Gemini model {model} returned an empty response. Please try again.")
        if index > 0:
            app.logger.info("LearnMind AI answered using fallback model %s.", model)
        return answer

    if last_transient_error is not None:
        raise GeminiTemporarilyUnavailable(
            "LearnMind AI is temporarily busy. Both configured Gemini models are unavailable. "
            "Please retry your question in a moment."
        ) from last_transient_error
    raise GeminiTemporarilyUnavailable(
        "LearnMind AI is temporarily unavailable. Please retry your question in a moment."
    )


def make_ai_answer(question: str, history: list[sqlite3.Row]) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured in your .env file.")

    from google import genai
    from google.genai import types

    transcript = []
    for item in history[-10:]:
        speaker = "Student" if item["role"] == "user" else "LearnMind AI"
        transcript.append(f"{speaker}: {item['content']}")
    transcript.append(f"Student: {question}")
    prompt = (
        "You are LearnMind AI, a patient academic study assistant for college students. "
        "Use clear, simple English. Explain difficult topics step by step, include a useful "
        "example, and structure longer answers with headings or short bullet lists. "
        "For programming, provide correct beginner-friendly code and explain it. "
        "Do not invent facts. If a question is ambiguous, briefly clarify your assumption.\n\n"
        + "\n".join(transcript) + "\nLearnMind AI:"
    )

    primary_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash"
    fallback_model = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite").strip()
    models = [primary_model]
    if fallback_model and fallback_model not in models:
        models.append(fallback_model)

    # Keep each SDK retry short; the application then switches to the fallback
    # model instead of making a student wait through the SDK's long default delay.
    retry_options = types.HttpRetryOptions(
        attempts=2,  # one original request plus one retry
        initial_delay=1.0,
        max_delay=3.0,
        exp_base=2.0,
        jitter=0.5,
        http_status_codes=sorted(TRANSIENT_GEMINI_STATUS_CODES),
    )
    http_options = types.HttpOptions(retry_options=retry_options)

    with genai.Client(api_key=api_key, http_options=http_options) as client:
        return _generate_with_model_fallback(client, models, prompt)


@app.get("/api/chat/history")
@login_required
def chat_history():
    rows = get_db().execute(
        "SELECT role, content, created_at FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT 60",
        (session["user_id"],),
    ).fetchall()
    messages = [dict(row) for row in reversed(rows)]
    return jsonify({"messages": messages})


@app.post("/api/chat/clear")
@login_required
def clear_chat():
    db = get_db()
    db.execute("DELETE FROM chat_messages WHERE user_id = ?", (session["user_id"],))
    db.commit()
    return jsonify({"ok": True})


@app.post("/ask_ai")
@app.post("/api/chat/send")
@login_required
def ask_ai():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")
    if not isinstance(question, str):
        return jsonify({"error": "Please enter a valid question."}), 400
    question = question.strip()
    if not question:
        return jsonify({"error": "Please enter your study question."}), 400
    if len(question) > 2000:
        return jsonify({"error": "Your question must be 2,000 characters or fewer."}), 400

    db = get_db()
    history = db.execute(
        "SELECT role, content FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT 10",
        (session["user_id"],),
    ).fetchall()
    history = list(reversed(history))
    try:
        answer = make_ai_answer(question, history)
    except GeminiTemporarilyUnavailable as exc:
        # This is an upstream provider outage, not an application crash.
        app.logger.warning("LearnMind Gemini is temporarily unavailable: %s", exc)
        return jsonify({"error": str(exc), "code": "AI_TEMPORARILY_UNAVAILABLE"}), 503
    except Exception as exc:
        status_code = _gemini_error_code(exc)
        if status_code in (401, 403):
            app.logger.error("Gemini rejected the configured credentials (HTTP %s).", status_code)
            return jsonify({
                "error": "Gemini rejected the API key or its permissions. Create a valid key in Google AI Studio and update GEMINI_API_KEY in .env.",
                "code": "GEMINI_AUTH_ERROR",
            }), 502
        if status_code == 429:
            app.logger.warning("Gemini request was rate-limited after fallback (HTTP 429).")
            return jsonify({
                "error": "Gemini is rate-limiting this project. Wait briefly and try again, or check the API quota for your key.",
                "code": "GEMINI_RATE_LIMITED",
            }), 429
        app.logger.exception("LearnMind Gemini request failed")
        message = str(exc) if isinstance(exc, RuntimeError) and "not configured" in str(exc) else "The AI service could not complete this request. Check the Gemini API key, model configuration and internet connection."
        return jsonify({"error": message, "code": "GEMINI_REQUEST_FAILED"}), 502

    created_at = now_iso()
    db.execute(
        "INSERT INTO chat_messages(user_id, role, content, created_at) VALUES (?, 'user', ?, ?)",
        (session["user_id"], question, created_at),
    )
    db.execute(
        "INSERT INTO chat_messages(user_id, role, content, created_at) VALUES (?, 'assistant', ?, ?)",
        (session["user_id"], answer, created_at),
    )
    db.commit()
    return jsonify({"answer": answer, "created_at": created_at})


@app.errorhandler(400)
def bad_request(error):
    if request.path.startswith("/api/") or request.path == "/ask_ai":
        return jsonify({"error": getattr(error, "description", "Bad request.")}), 400
    return render_template("error.html", code=400, message=getattr(error, "description", "Bad request.")), 400


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "The requested item was not found."}), 404
    return render_template("error.html", code=404, message="The page you requested could not be found."), 404


@app.errorhandler(500)
def server_error(error):
    app.logger.error(
        "Unhandled LearnMind server error",
        exc_info=(type(error), error, error.__traceback__),
    )
    if request.path.startswith("/api/") or request.path == "/ask_ai":
        return jsonify({"error": "A server error occurred. Check the VS Code terminal for details."}), 500
    return render_template("error.html", code=500, message="Something went wrong. Please try again."), 500


# Initialize schema when imported by Flask or run directly.
with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "1") == "1")
