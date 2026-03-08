"""
tests/test_app.py
Pytest test suite for ACEest Fitness Flask Application
"""

import os
import tempfile
import pytest


# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

@pytest.fixture
def client():
    """Create a test client with a fresh temporary database file."""
    # Use a real temp file so all connections share the same data
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.environ["DB_PATH"] = db_path

    # Import AFTER setting DB_PATH so the module picks it up
    from app import app, init_db
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"

    with app.test_client() as c:
        with app.app_context():
            init_db()
        yield c

    # Cleanup: close the fd and remove temp file
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def logged_in_client(client):
    """Return a test client that is already logged in as admin."""
    client.post("/login", data={"username": "admin", "password": "admin123"},
                follow_redirects=True)
    return client


# ─────────────────────────────────────────────
# HEALTH & HOME
# ─────────────────────────────────────────────

def test_health_endpoint(client):
    """Health check should return 200 and status ok."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"


def test_root_redirects_to_login(client):
    """Unauthenticated root request should redirect to login page."""
    res = client.get("/", follow_redirects=False)
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


# ─────────────────────────────────────────────
# AUTHENTICATION
# ─────────────────────────────────────────────

def test_login_page_loads(client):
    """Login page should return 200."""
    res = client.get("/login")
    assert res.status_code == 200
    assert b"Login" in res.data


def test_login_with_valid_credentials(client):
    """Valid credentials should redirect to dashboard."""
    res = client.post("/login",
                      data={"username": "admin", "password": "admin123"},
                      follow_redirects=True)
    assert res.status_code == 200
    assert b"Dashboard" in res.data or b"ACEest" in res.data


def test_login_with_invalid_credentials(client):
    """Invalid credentials should show error message."""
    res = client.post("/login",
                      data={"username": "admin", "password": "wrongpass"},
                      follow_redirects=True)
    assert res.status_code == 200
    assert b"Invalid" in res.data


def test_logout(logged_in_client):
    """Logout should clear session and redirect to login."""
    res = logged_in_client.get("/logout", follow_redirects=True)
    assert res.status_code == 200
    assert b"Login" in res.data or b"logged out" in res.data


# ─────────────────────────────────────────────
# PROTECTED ROUTES
# ─────────────────────────────────────────────

def test_dashboard_requires_login(client):
    """Dashboard should redirect to login for unauthenticated users."""
    res = client.get("/dashboard", follow_redirects=False)
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_clients_page_requires_login(client):
    """Clients page should redirect to login for unauthenticated users."""
    res = client.get("/clients", follow_redirects=False)
    assert res.status_code == 302


def test_dashboard_loads_after_login(logged_in_client):
    """Dashboard should load successfully after login."""
    res = logged_in_client.get("/dashboard")
    assert res.status_code == 200


# ─────────────────────────────────────────────
# CLIENT MANAGEMENT
# ─────────────────────────────────────────────

def test_add_client_page_loads(logged_in_client):
    """Add-client form page should return 200."""
    res = logged_in_client.get("/add_client")
    assert res.status_code == 200


def test_add_client_successfully(logged_in_client):
    """Submitting a valid client form should create a client and redirect."""
    res = logged_in_client.post("/add_client", data={
        "name": "Ravi Kumar",
        "age": "28",
        "height": "175",
        "weight": "75",
        "program": "Fat Loss (FL)",
        "target_weight": "70",
        "membership_status": "Active"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Ravi Kumar" in res.data


def test_add_client_missing_fields(logged_in_client):
    """Form submission without required fields should show error."""
    res = logged_in_client.post("/add_client", data={
        "name": "",
        "program": ""
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"required" in res.data.lower()


def test_clients_list_page(logged_in_client):
    """Clients listing page should load and show existing clients."""
    # First add a client
    logged_in_client.post("/add_client", data={
        "name": "Priya Devi",
        "age": "25",
        "height": "165",
        "weight": "60",
        "program": "Beginner (BG)",
        "membership_status": "Active"
    })
    res = logged_in_client.get("/clients")
    assert res.status_code == 200
    assert b"Priya Devi" in res.data


# ─────────────────────────────────────────────
# FITNESS PROGRAMS LOGIC
# ─────────────────────────────────────────────

def test_programs_are_defined():
    """All three fitness programs should be present."""
    from app import PROGRAMS
    assert "Fat Loss (FL)" in PROGRAMS
    assert "Muscle Gain (MG)" in PROGRAMS
    assert "Beginner (BG)" in PROGRAMS


def test_fat_loss_calorie_factor():
    """Fat Loss calorie factor should be 22."""
    from app import PROGRAMS
    assert PROGRAMS["Fat Loss (FL)"]["calorie_factor"] == 22


def test_muscle_gain_calorie_factor():
    """Muscle Gain calorie factor should be 35."""
    from app import PROGRAMS
    assert PROGRAMS["Muscle Gain (MG)"]["calorie_factor"] == 35


def test_beginner_calorie_factor():
    """Beginner calorie factor should be 26."""
    from app import PROGRAMS
    assert PROGRAMS["Beginner (BG)"]["calorie_factor"] == 26


def test_calorie_calculation():
    """Calories = weight_kg × calorie_factor."""
    from app import PROGRAMS
    weight = 80.0
    program = "Fat Loss (FL)"
    expected = int(weight * PROGRAMS[program]["calorie_factor"])
    assert expected == 1760


def test_all_programs_have_workout_plans():
    """Every program must include a workout description."""
    from app import PROGRAMS
    for name, info in PROGRAMS.items():
        assert "workout" in info, f"No workout in program: {name}"
        assert len(info["workout"]) > 0


def test_all_programs_have_diet_plans():
    """Every program must include a diet description."""
    from app import PROGRAMS
    for name, info in PROGRAMS.items():
        assert "diet" in info, f"No diet in program: {name}"
        assert len(info["diet"]) > 0


# ─────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────

def test_api_programs_returns_json(client):
    """Public /api/programs endpoint should return JSON."""
    res = client.get("/api/programs")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, dict)
    assert "Fat Loss (FL)" in data


def test_api_clients_requires_login(client):
    """Protected /api/clients endpoint should reject unauthenticated requests."""
    res = client.get("/api/clients", follow_redirects=False)
    assert res.status_code == 302


def test_api_clients_returns_list(logged_in_client):
    """Authenticated /api/clients should return a JSON list."""
    res = logged_in_client.get("/api/clients")
    assert res.status_code == 200
    assert isinstance(res.get_json(), list)


# ─────────────────────────────────────────────
# WORKOUT LOGGING
# ─────────────────────────────────────────────

def test_add_workout_page_loads(logged_in_client):
    """Add-workout form should return 200."""
    res = logged_in_client.get("/add_workout")
    assert res.status_code == 200


def test_add_workout_for_client(logged_in_client):
    """Submitting a workout for an existing client should succeed."""
    # Create client first
    logged_in_client.post("/add_client", data={
        "name": "Arjun S",
        "age": "30",
        "height": "180",
        "weight": "85",
        "program": "Muscle Gain (MG)",
        "membership_status": "Active"
    })
    res = logged_in_client.post("/add_workout", data={
        "client_name": "Arjun S",
        "date": "2025-01-01",
        "workout_type": "Strength",
        "duration_min": "60",
        "notes": "Great session"
    }, follow_redirects=True)
    assert res.status_code == 200
