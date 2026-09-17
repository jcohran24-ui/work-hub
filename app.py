import os
import re
from urllib.parse import urlparse

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:
    psycopg = None

import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "field-hub-project-selection")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
)

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

DEFAULT_APPS = [
    ("schedule", "Schedule", "📅", "Look-aheads, subcontractor updates, delays and progress", os.environ.get("SCHEDULE_URL", ""), "View Schedule", "Schedule information", 10),
    ("timesheets", "Timesheets", "⏱️", "Employee hours, approvals and weekly reports", os.environ.get("TIMESHEETS_URL", ""), "Enter Hours", "Weekly hours", 20),
    ("manpower", "Manpower", "👷", "Daily subcontractor manpower and manhours", os.environ.get("MANPOWER_URL", ""), "Today's Manpower", "Daily field count", 30),
    ("equipment", "Equipment", "🚜", "Rental equipment, delivery dates and pickup dates", os.environ.get("EQUIPMENT_URL", ""), "Open Equipment", "Equipment onsite", 40),
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

    # Remove retired hub modules from existing databases as well as fresh installs.
    retired_slugs = ("specialty", "inspections", "safety", "contacts", "documents")
    for retired_slug in retired_slugs:
        row = execute("SELECT id FROM apps WHERE slug=?", (retired_slug,), fetchone=True)
        if row:
            execute("DELETE FROM project_apps WHERE app_id=?", (row["id"],), commit=True)
            execute("DELETE FROM apps WHERE id=?", (row["id"],), commit=True)

    # Upgrade a V2 database in place by leaving any old users/min_role columns alone.
    # The no-login version simply does not use them.
    if not execute("SELECT id FROM projects LIMIT 1", fetchone=True):
        for slug, name, active in DEFAULT_PROJECTS:
            execute("INSERT INTO projects (slug, name, active) VALUES (?, ?, ?)", (slug, name, active), commit=True)

    if not execute("SELECT id FROM apps LIMIT 1", fetchone=True):
        for item in DEFAULT_APPS:
            execute(
                """INSERT INTO apps (slug,name,icon,description,url,quick_label,metric_label,min_role,sort_order,active)
                   VALUES (?,?,?,?,?,?,?,'field',?,TRUE)""",
                item,
                commit=True,
            )

    if not execute("SELECT project_id FROM project_apps LIMIT 1", fetchone=True):
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


def list_projects():
    return execute("SELECT * FROM projects WHERE active=TRUE ORDER BY name", fetchall=True)


def selected_project(projects):
    if not projects:
        return None
    selected_id = session.get("project_id")
    project = next((p for p in projects if p["id"] == selected_id), projects[0])
    session["project_id"] = project["id"]
    return project


def apps_for_project(project_id):
    return execute(
        """SELECT a.* FROM apps a
           JOIN project_apps pa ON pa.app_id=a.id
           WHERE pa.project_id=? AND pa.enabled=TRUE AND a.active=TRUE
           ORDER BY a.sort_order, a.name""",
        (project_id,), fetchall=True,
    )


@app.route("/")
def home():
    projects = list_projects()
    project = selected_project(projects)
    apps_rows = apps_for_project(project["id"]) if project else []
    dashboard = {
        "workers": "—",
        "subcontractors": "—",
        "inspections": "—",
        "equipment": "—",
    }
    return render_template("index.html", projects=projects, project=project, apps=apps_rows, dashboard=dashboard)


@app.post("/project")
def set_project():
    try:
        project_id = int(request.form.get("project_id", "0"))
    except ValueError:
        project_id = 0
    if execute("SELECT id FROM projects WHERE id=? AND active=TRUE", (project_id,), fetchone=True):
        session["project_id"] = project_id
    return redirect(url_for("home"))


@app.route("/admin")
def admin():
    projects = execute("SELECT * FROM projects ORDER BY active DESC, name", fetchall=True)
    apps_rows = execute("SELECT * FROM apps ORDER BY active DESC, sort_order, name", fetchall=True)
    return render_template("admin.html", projects=projects, apps=apps_rows, db_kind=db_kind())


@app.post("/admin/projects/add")
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
        flash("That project ID is already in use.", "error")
    return redirect(url_for("admin"))


@app.post("/admin/projects/<int:project_id>/toggle")
def toggle_project(project_id):
    row = execute("SELECT active FROM projects WHERE id=?", (project_id,), fetchone=True)
    if row:
        execute("UPDATE projects SET active=? WHERE id=?", (not bool(row["active"]), project_id), commit=True)
    return redirect(url_for("admin"))


@app.post("/admin/apps/add")
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
    try:
        execute(
            """INSERT INTO apps (slug,name,icon,description,url,quick_label,metric_label,min_role,sort_order,active)
               VALUES (?,?,?,?,?,?,?,'field',100,TRUE)""",
            (slug, name, icon, description, url, quick, ""), commit=True,
        )
        app_row = execute("SELECT id FROM apps WHERE slug=?", (slug,), fetchone=True)
        for p in execute("SELECT id FROM projects", fetchall=True):
            execute("INSERT INTO project_apps (project_id,app_id,enabled) VALUES (?, ?, TRUE)", (p["id"], app_row["id"]), commit=True)
        flash("App added to the hub.", "success")
    except Exception:
        flash("That app ID is already in use.", "error")
    return redirect(url_for("admin"))


@app.post("/admin/apps/<int:app_id>/edit")
def edit_app(app_id):
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    if not name or not valid_url(url):
        flash("Check the app name and URL.", "error")
        return redirect(url_for("admin"))
    try:
        sort_order = int(request.form.get("sort_order", "100"))
    except ValueError:
        sort_order = 100
    execute(
        """UPDATE apps SET name=?, icon=?, description=?, url=?, quick_label=?, metric_label=?, sort_order=? WHERE id=?""",
        (
            name,
            request.form.get("icon", "🔗").strip() or "🔗",
            request.form.get("description", "").strip(),
            url,
            request.form.get("quick_label", "Open App").strip() or "Open App",
            request.form.get("metric_label", "").strip(),
            sort_order,
            app_id,
        ),
        commit=True,
    )
    flash("App updated.", "success")
    return redirect(url_for("admin"))


@app.post("/admin/apps/<int:app_id>/toggle")
def toggle_app(app_id):
    row = execute("SELECT active FROM apps WHERE id=?", (app_id,), fetchone=True)
    if row:
        execute("UPDATE apps SET active=? WHERE id=?", (not bool(row["active"]), app_id), commit=True)
    return redirect(url_for("admin"))


@app.route("/health")
def health():
    return jsonify({"status": "ok", "database": db_kind(), "authentication": "none"})


try:
    init_db()
except Exception as exc:
    print(f"Database initialization failed: {exc}")

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=os.environ.get("FLASK_DEBUG") == "1")
