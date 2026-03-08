"""
ACEest Fitness & Gym - Flask Web Application
Assignment: DevOps CI/CD Pipeline Implementation
"""

import os
import sqlite3
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "aceest-devops-secret-2025")

DB_NAME = os.environ.get("DB_PATH", "aceest_fitness.db")

# ─────────────────────────────────────────────
# FITNESS PROGRAMS (business logic from original scripts)
# ─────────────────────────────────────────────
PROGRAMS = {
    "Fat Loss (FL)": {
        "calorie_factor": 22,
        "workout": "Mon: Back Squat 5x5 + Core\nTue: EMOM 20min Assault Bike\nWed: Bench Press + 21-15-9\nThu: Deadlift + Box Jumps\nFri: Zone 2 Cardio 30min",
        "diet": "Breakfast: Egg Whites + Oats\nLunch: Grilled Chicken + Brown Rice\nDinner: Fish Curry + Millet Roti\nTarget: ~2000 kcal"
    },
    "Muscle Gain (MG)": {
        "calorie_factor": 35,
        "workout": "Mon: Squat 5x5\nTue: Bench 5x5\nWed: Deadlift 4x6\nThu: Front Squat 4x8\nFri: Incline Press 4x10\nSat: Barbell Rows 4x10",
        "diet": "Breakfast: Eggs + Peanut Butter Oats\nLunch: Chicken Biryani\nDinner: Mutton Curry + Rice\nTarget: ~3200 kcal"
    },
    "Beginner (BG)": {
        "calorie_factor": 26,
        "workout": "Full Body Circuit:\n- Air Squats\n- Ring Rows\n- Push-ups\nFocus: Technique & Consistency",
        "diet": "Balanced Tamil Meals\nIdli / Dosa / Rice + Dal\nProtein Target: 120g/day"
    }
}

# ─────────────────────────────────────────────
# DATABASE HELPERS
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role     TEXT NOT NULL DEFAULT 'Staff'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT UNIQUE NOT NULL,
            age             INTEGER,
            height          REAL,
            weight          REAL,
            program         TEXT,
            calories        INTEGER,
            target_weight   REAL,
            membership_status TEXT DEFAULT 'Active',
            created_at      TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            week        TEXT NOT NULL,
            adherence   INTEGER NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name  TEXT NOT NULL,
            date         TEXT NOT NULL,
            workout_type TEXT,
            duration_min INTEGER,
            notes        TEXT
        )
    """)

    # Seed default admin user
    cur.execute(
        "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
        ("admin", "admin123", "Admin")
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# AUTH DECORATOR
# ─────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    total_clients = conn.execute("SELECT COUNT(*) AS cnt FROM clients").fetchone()["cnt"]
    active_clients = conn.execute(
        "SELECT COUNT(*) AS cnt FROM clients WHERE membership_status = 'Active'"
    ).fetchone()["cnt"]
    recent_workouts = conn.execute(
        "SELECT * FROM workouts ORDER BY id DESC LIMIT 5"
    ).fetchall()
    conn.close()
    return render_template("dashboard.html",
                           total_clients=total_clients,
                           active_clients=active_clients,
                           recent_workouts=recent_workouts,
                           programs=PROGRAMS)


@app.route("/clients")
@login_required
def clients():
    conn = get_db()
    all_clients = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
    conn.close()
    return render_template("clients.html", clients=all_clients)


@app.route("/add_client", methods=["GET", "POST"])
@login_required
def add_client():
    if request.method == "POST":
        name   = request.form.get("name", "").strip()
        age    = request.form.get("age", 0)
        height = request.form.get("height", 0.0)
        weight = request.form.get("weight", 0.0)
        program = request.form.get("program", "")
        target_weight = request.form.get("target_weight", 0.0)
        membership_status = request.form.get("membership_status", "Active")

        if not name or not program:
            flash("Name and Program are required.", "danger")
            return render_template("add_client.html", programs=PROGRAMS)

        try:
            weight_f = float(weight)
            factor   = PROGRAMS.get(program, {}).get("calorie_factor", 25)
            calories = int(weight_f * factor) if weight_f > 0 else None
        except ValueError:
            calories = None

        conn = get_db()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO clients
                   (name, age, height, weight, program, calories, target_weight,
                    membership_status, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (name, age, height, weight, program, calories,
                 target_weight, membership_status, date.today().isoformat())
            )
            conn.commit()
            flash(f"Client '{name}' saved successfully!", "success")
            return redirect(url_for("clients"))
        except Exception as e:
            flash(f"Error saving client: {e}", "danger")
        finally:
            conn.close()

    return render_template("add_client.html", programs=PROGRAMS)


@app.route("/client/<name>")
@login_required
def client_detail(name):
    conn = get_db()
    client = conn.execute("SELECT * FROM clients WHERE name = ?", (name,)).fetchone()
    if not client:
        flash("Client not found.", "warning")
        conn.close()
        return redirect(url_for("clients"))

    workouts = conn.execute(
        "SELECT * FROM workouts WHERE client_name = ? ORDER BY date DESC",
        (name,)
    ).fetchall()
    progress = conn.execute(
        "SELECT * FROM progress WHERE client_name = ? ORDER BY id",
        (name,)
    ).fetchall()
    conn.close()

    program_info = PROGRAMS.get(client["program"], {})
    return render_template("client_detail.html",
                           client=client,
                           workouts=workouts,
                           progress=progress,
                           program_info=program_info)


@app.route("/add_workout", methods=["GET", "POST"])
@login_required
def add_workout():
    conn = get_db()
    all_clients = conn.execute("SELECT name FROM clients ORDER BY name").fetchall()

    if request.method == "POST":
        client_name  = request.form.get("client_name", "").strip()
        workout_date = request.form.get("date", date.today().isoformat())
        workout_type = request.form.get("workout_type", "")
        duration     = request.form.get("duration_min", 60)
        notes        = request.form.get("notes", "")

        if not client_name or not workout_type:
            flash("Client and Workout Type are required.", "danger")
        else:
            try:
                conn.execute(
                    """INSERT INTO workouts
                       (client_name, date, workout_type, duration_min, notes)
                       VALUES (?,?,?,?,?)""",
                    (client_name, workout_date, workout_type, duration, notes)
                )
                conn.commit()
                flash("Workout logged successfully!", "success")
                conn.close()
                return redirect(url_for("client_detail", name=client_name))
            except Exception as e:
                flash(f"Error: {e}", "danger")

    conn.close()
    return render_template("add_workout.html", clients=all_clients)


@app.route("/save_progress", methods=["POST"])
@login_required
def save_progress():
    client_name = request.form.get("client_name", "").strip()
    adherence   = request.form.get("adherence", 0)
    week        = datetime.now().strftime("Week %U - %Y")

    conn = get_db()
    conn.execute(
        "INSERT INTO progress (client_name, week, adherence) VALUES (?,?,?)",
        (client_name, week, adherence)
    )
    conn.commit()
    conn.close()

    flash("Weekly progress saved!", "success")
    return redirect(url_for("client_detail", name=client_name))


@app.route("/api/programs")
def api_programs():
    """JSON endpoint – returns available fitness programs."""
    return jsonify({name: {"calorie_factor": info["calorie_factor"]}
                    for name, info in PROGRAMS.items()})


@app.route("/api/clients")
@login_required
def api_clients():
    """JSON endpoint – returns all clients (used by tests)."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/health")
def health():
    """Health-check endpoint for CI/CD pipeline."""
    return jsonify({"status": "ok", "app": "ACEest Fitness"}), 200


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
