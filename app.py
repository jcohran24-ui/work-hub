import os
import re
from functools import wraps
from urllib.parse import urlparse

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:
    psycopg = None

import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-render")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
)

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
ROLE_RANK = {"field": 1, "superintendent": 2, "admin": 3}

DEFAULT_APPS = [
    ("schedule", "Schedule", "📅", "Look-aheads, subcontractor updates, delays and progress", os.environ.get("SCHEDULE_URL", ""), "View Schedule", "Schedule information", "field", 10),
    ("timesheets", "Timesheets", "⏱️", "Employee hours, approvals and weekly reports", os.environ.get("TIMESHEETS_URL", ""), "Enter Hours", "Weekly hours", "field", 20),
    ("manpower", "Manpower", "👷", "Daily subcontractor manpower and manhours", os.environ.get("MANPOWER_URL", ""), "Today's Manpower", "Daily field count", "field", 30),
    ("equipment", "Equipment", "🚜", "Rental equipment, delivery dates and pickup dates", os.environ.get("EQUIPMENT_URL", ""), "Open Equipment", "Equipment onsite", "field", 40),
    ("specialty", "Specialty Subs", "🔨", "Track specialty subcontractors and site visits", os.environ.get("SPECIALTY_URL", ""), "Open Tracker", "Upcoming visits", "field", 50),
    ("inspections", "Inspections", "🔍", "Requested dates, inspection type and status", os.environ.get("INSPECTIONS_URL", ""), "Open Inspections", "Open inspections", "field", 60),
    ("safety", "Safety", "🦺", "Observations, incidents and corrective actions", os.environ.get("SAFETY_URL", ""), "Open Safety", "Safety items", "field", 70),
    ("contacts", "Contacts", "📇", "Project contacts, inspectors, vendors and subs", os.environ.get("CONTACTS_URL", ""), "Find Contact", "Project directory", "field", 80),
    ("documents", "Documents", "📁", "Forms, QR sheets and frequently used project files", os.environ.get("DOCUMENTS_URL", ""), "Open Documents", "Shared files", "field", 90),
]

DEFAULT_PROJECTS = [
    ("oasis", "Oasis – Cherokee Town & Country Club", True),
]


def db_kind():
    return "postgres" if DATABASE_URL and psycopg else "sqlite"


def get_conn():
    if db_kind() == "postgres":
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    path = os.environ.get("SQLITE_PATH", "/tmp/field_hub.db")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def qmark(sql):
    return sql.replace("?", "%s") if db_kind() == "postgres" else sql


def execute(sql, params=(), fetchone=False, fetchall=False, commit=False):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(qmark(sql), params)
        result = None
        if fetchone:
            row = cur.fetchone()
            result = dict(row) if row else None
        elif fetchall:
            result = [dict(r) for r in cur.fetchall()]
        if commit:
            conn.commit()
        return result


def init_db():
    id_type = "SERIAL PRIMARY KEY" if db_kind() == "postgres" else "INTEGER PRIMARY KEY"
    statements = [
        f"""
        CREATE TABLE IF NOT EXISTS users (
            id {id_type},
            username VARCHAR(80) UNIQUE NOT NULL,
            display_name VARCHAR(120) NOT NULL,
            password_hash TEXT NOT NULL,
            role VARCHAR(30) NOT NULL DEFAULT 'field',
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS projects (
            id {id_type},
            slug VARCHAR(80) UNIQUE NOT NULL,
            name VARCHAR(180) NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS apps (
            id {id_type},
            slug VARCHAR(80) UNIQUE NOT NULL,
            name VARCHAR(120) NOT NULL,
            icon VARCHAR(20) NOT NULL DEFAULT '🔗',
            description TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL DEFAULT '',
            quick_label VARCHAR(80) NOT NULL DEFAULT 'Open App',
            metric_label VARCHAR(120) NOT NULL DEFAULT '',
            min_role VARCHAR(30) NOT NULL DEFAULT 'field',
            sort_order INTEGER NOT NULL DEFAULT 100,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS project_apps (
            project_id INTEGER NOT NULL,
            app_id INTEGER NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            PRIMARY KEY(project_id, app_id)
        )
        """,
    ]
    with get_conn() as conn:
        cur = conn.cursor()
        for stmt in statements:
            cur.execute(stmt)
        conn.commit()

    # Seed projects/apps only when empty.
    if not execute("SELECT id FROM projects LIMIT 1", fetchone=True):
        for slug, name, active in DEFAULT_PROJECTS:
            execute("INSERT INTO projects (slug, name, active) VALUES (?, ?, ?)", (slug, name, active), commit=True)
    if not execute("SELECT id FROM apps LIMIT 1", fetchone=True):
        for item in DEFAULT_APPS:
            execute(
                """INSERT INTO apps (slug,name,icon,description,url,quick_label,metric_label,min_role,sort_order,active)
                   VALUES (?,?,?,?,?,?,?,?,?,TRUE)""",
                item,
                commit=True,
            )

    # Bootstrap admin.
    if not execute("SELECT id FROM users LIMIT 1", fetchone=True):
        username = os.environ.get("ADMIN_USERNAME", "admin").strip().lower()
        password = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")
        display_name = os.environ.get("ADMIN_DISPLAY_NAME", "Administrator")
        execute(
            "INSERT INTO users (username, display_name, password_hash, role, active) VALUES (?, ?, ?, 'admin', TRUE)",
            (username, display_name, generate_password_hash(password)),
            commit=True,
        )

    # Enable all apps for all projects if no mapping exists.
    mapping = execute("SELECT project_id FROM project_apps LIMIT 1", fetchone=True)
    if not mapping:
        projects = execute("SELECT id FROM projects", fetchall=True)
        apps_rows = execute("SELECT id FROM apps", fetchall=True)
        for p in projects:
            for a in apps_rows:
                try:
                    execute("INSERT INTO project_apps (project_id, app_id, enabled) VALUES (?, ?, TRUE)", (p["id"], a["id"]), commit=True)
                except Exception:
                    pass


def valid_url(value):
    if not value:
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def slugify(value):
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:70] or "item"


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Administrator access is required.", "error")
            return redirect(url_for("home"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    if not session.get("user_id"):
        return None
    return {
        "id": session.get("user_id"),
        "username": session.get("username"),
        "display_name": session.get("display_name"),
        "role": session.get("role"),
    }


def list_projects():
    return execute("SELECT * FROM projects WHERE active=TRUE ORDER BY name", fetchall=True)


def selected_project(projects):
    if not projects:
        return None
    selected_id = session.get("project_id")
    project = next((p for p in projects if p["id"] == selected_id), projects[0])
    session["project_id"] = project["id"]
    return project


def apps_for_project(project_id, role):
    rows = execute(
        """SELECT a.* FROM apps a
           JOIN project_apps pa ON pa.app_id=a.id
           WHERE pa.project_id=? AND pa.enabled=TRUE AND a.active=TRUE
           ORDER BY a.sort_order, a.name""",
        (project_id,), fetchall=True,
    )
    rank = ROLE_RANK.get(role, 1)
    return [a for a in rows if rank >= ROLE_RANK.get(a.get("min_role", "field"), 1)]


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("home"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = execute("SELECT * FROM users WHERE username=? AND active=TRUE", (username,), fetchone=True)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update(
                user_id=user["id"], username=user["username"], display_name=user["display_name"], role=user["role"]
            )
            return redirect(request.args.get("next") or url_for("home"))
        flash("Incorrect username or password.", "error")
    return render_template("login.html")


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    projects = list_projects()
    project = selected_project(projects)
    apps_rows = apps_for_project(project["id"], session.get("role", "field")) if project else []
    dashboard = {
        "workers": "—",
        "subcontractors": "—",
        "inspections": "—",
        "equipment": "—",
        "alerts": 0,
    }
    return render_template("index.html", projects=projects, project=project, apps=apps_rows, dashboard=dashboard, user=current_user())


@app.post("/project")
@login_required
def set_project():
    try:
        project_id = int(request.form.get("project_id", "0"))
    except ValueError:
        project_id = 0
    if execute("SELECT id FROM projects WHERE id=? AND active=TRUE", (project_id,), fetchone=True):
        session["project_id"] = project_id
    return redirect(url_for("home"))


@app.route("/admin")
@admin_required
def admin():
    projects = execute("SELECT * FROM projects ORDER BY active DESC, name", fetchall=True)
    apps_rows = execute("SELECT * FROM apps ORDER BY active DESC, sort_order, name", fetchall=True)
    users = execute("SELECT id,username,display_name,role,active,created_at FROM users ORDER BY active DESC, display_name", fetchall=True)
    return render_template("admin.html", projects=projects, apps=apps_rows, users=users, user=current_user(), db_kind=db_kind())


@app.post("/admin/projects/add")
@admin_required
def add_project():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Project name is required.", "error")
        return redirect(url_for("admin"))
    slug = slugify(request.form.get("slug", "") or name)
    try:
        execute("INSERT INTO projects (slug,name,active) VALUES (?, ?, TRUE)", (slug, name), commit=True)
        project = execute("SELECT id FROM projects WHERE slug=?", (slug,), fetchone=True)
        apps_rows = execute("SELECT id FROM apps", fetchall=True)
        for a in apps_rows:
            execute("INSERT INTO project_apps (project_id,app_id,enabled) VALUES (?, ?, TRUE)", (project["id"], a["id"]), commit=True)
        flash("Project added.", "success")
    except Exception:
        flash("That project slug is already in use.", "error")
    return redirect(url_for("admin"))


@app.post("/admin/projects/<int:project_id>/toggle")
@admin_required
def toggle_project(project_id):
    row = execute("SELECT active FROM projects WHERE id=?", (project_id,), fetchone=True)
    if row:
        execute("UPDATE projects SET active=? WHERE id=?", (not bool(row["active"]), project_id), commit=True)
    return redirect(url_for("admin"))


@app.post("/admin/apps/add")
@admin_required
def add_app():
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    if not name or not valid_url(url):
        flash("Enter an app name and a valid http/https URL.", "error")
        return redirect(url_for("admin"))
    slug = slugify(request.form.get("slug", "") or name)
    icon = request.form.get("icon", "🔗").strip() or "🔗"
    description = request.form.get("description", "").strip()
    quick = request.form.get("quick_label", "Open App").strip() or "Open App"
    min_role = request.form.get("min_role", "field")
    if min_role not in ROLE_RANK:
        min_role = "field"
    try:
        execute(
            """INSERT INTO apps (slug,name,icon,description,url,quick_label,metric_label,min_role,sort_order,active)
               VALUES (?,?,?,?,?,?,?, ?,100,TRUE)""",
            (slug, name, icon, description, url, quick, "", min_role), commit=True,
        )
        app_row = execute("SELECT id FROM apps WHERE slug=?", (slug,), fetchone=True)
        for p in execute("SELECT id FROM projects", fetchall=True):
            execute("INSERT INTO project_apps (project_id,app_id,enabled) VALUES (?, ?, TRUE)", (p["id"], app_row["id"]), commit=True)
        flash("App added to the hub.", "success")
    except Exception:
        flash("That app slug is already in use.", "error")
    return redirect(url_for("admin"))


@app.post("/admin/apps/<int:app_id>/edit")
@admin_required
def edit_app(app_id):
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    min_role = request.form.get("min_role", "field")
    if not name or not valid_url(url) or min_role not in ROLE_RANK:
        flash("Check the app name, URL and role.", "error")
        return redirect(url_for("admin"))
    try:
        sort_order = int(request.form.get("sort_order", "100"))
    except ValueError:
        sort_order = 100
    execute(
        """UPDATE apps SET name=?, icon=?, description=?, url=?, quick_label=?, metric_label=?, min_role=?, sort_order=? WHERE id=?""",
        (
            name,
            request.form.get("icon", "🔗").strip() or "🔗",
            request.form.get("description", "").strip(),
            url,
            request.form.get("quick_label", "Open App").strip() or "Open App",
            request.form.get("metric_label", "").strip(),
            min_role,
            sort_order,
            app_id,
        ),
        commit=True,
    )
    flash("App updated.", "success")
    return redirect(url_for("admin"))


@app.post("/admin/apps/<int:app_id>/toggle")
@admin_required
def toggle_app(app_id):
    row = execute("SELECT active FROM apps WHERE id=?", (app_id,), fetchone=True)
    if row:
        execute("UPDATE apps SET active=? WHERE id=?", (not bool(row["active"]), app_id), commit=True)
    return redirect(url_for("admin"))


@app.post("/admin/users/add")
@admin_required
def add_user():
    username = request.form.get("username", "").strip().lower()
    display_name = request.form.get("display_name", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "field")
    if not username or not display_name or len(password) < 8 or role not in ROLE_RANK:
        flash("User needs a name, username, role and password of at least 8 characters.", "error")
        return redirect(url_for("admin"))
    try:
        execute(
            "INSERT INTO users (username,display_name,password_hash,role,active) VALUES (?,?,?,?,TRUE)",
            (username, display_name, generate_password_hash(password), role), commit=True,
        )
        flash("User added.", "success")
    except Exception:
        flash("That username is already in use.", "error")
    return redirect(url_for("admin"))


@app.post("/admin/users/<int:user_id>/toggle")
@admin_required
def toggle_user(user_id):
    if user_id == session.get("user_id"):
        flash("You cannot disable your own account while signed in.", "error")
        return redirect(url_for("admin"))
    row = execute("SELECT active FROM users WHERE id=?", (user_id,), fetchone=True)
    if row:
        execute("UPDATE users SET active=? WHERE id=?", (not bool(row["active"]), user_id), commit=True)
    return redirect(url_for("admin"))


@app.post("/admin/users/<int:user_id>/password")
@admin_required
def reset_user_password(user_id):
    password = request.form.get("password", "")
    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
    else:
        execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(password), user_id), commit=True)
        flash("Password updated.", "success")
    return redirect(url_for("admin"))


@app.route("/health")
def health():
    return jsonify({"status": "ok", "database": db_kind()})


@app.context_processor
def inject_helpers():
    return {"role_labels": {"field": "Field", "superintendent": "Superintendent", "admin": "Administrator"}}


try:
    init_db()
except Exception as exc:
    print(f"Database initialization failed: {exc}")

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=os.environ.get("FLASK_DEBUG") == "1")
