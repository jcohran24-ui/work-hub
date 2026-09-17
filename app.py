from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-me-in-render')

PROJECTS = [
    {"id": "oasis", "name": "Oasis – Cherokee Town & Country Club"},
    {"id": "future", "name": "Future Project"},
]

APPS = [
    {"id": "schedule", "name": "Schedule", "icon": "📅", "description": "Look-aheads, subcontractor updates, delays and progress", "url": os.environ.get("SCHEDULE_URL", "#"), "quick": "View Schedule", "metric": "3 activities need attention"},
    {"id": "timesheets", "name": "Timesheets", "icon": "⏱️", "description": "Employee hours, approvals and weekly reports", "url": os.environ.get("TIMESHEETS_URL", "#"), "quick": "Enter Hours", "metric": "Weekly hours"},
    {"id": "manpower", "name": "Manpower", "icon": "👷", "description": "Daily subcontractor manpower and manhours", "url": os.environ.get("MANPOWER_URL", "#"), "quick": "Today's Manpower", "metric": "Daily field count"},
    {"id": "equipment", "name": "Equipment", "icon": "🚜", "description": "Rental equipment, delivery dates and pickup dates", "url": os.environ.get("EQUIPMENT_URL", "#"), "quick": "Add Equipment", "metric": "Equipment onsite"},
    {"id": "specialty", "name": "Specialty Subs", "icon": "🔨", "description": "Track specialty subcontractors and site visits", "url": os.environ.get("SPECIALTY_URL", "#"), "quick": "Log Visit", "metric": "Upcoming visits"},
    {"id": "inspections", "name": "Inspections", "icon": "🔍", "description": "Requested dates, inspection type and status", "url": os.environ.get("INSPECTIONS_URL", "#"), "quick": "Request Inspection", "metric": "Open inspections"},
    {"id": "safety", "name": "Safety", "icon": "🦺", "description": "Observations, incidents and corrective actions", "url": os.environ.get("SAFETY_URL", "#"), "quick": "Create Observation", "metric": "Safety items"},
    {"id": "contacts", "name": "Contacts", "icon": "📇", "description": "Project contacts, inspectors, vendors and subs", "url": os.environ.get("CONTACTS_URL", "#"), "quick": "Find Contact", "metric": "Project directory"},
    {"id": "documents", "name": "Documents", "icon": "📁", "description": "Forms, QR sheets and frequently used project files", "url": os.environ.get("DOCUMENTS_URL", "#"), "quick": "Open Documents", "metric": "Shared files"},
]

QUICK_ACTIONS = [
    "Equipment", "Manpower", "Inspection", "Safety Observation", "Delivery",
    "Specialty Sub Visit", "Schedule Issue", "Contact", "Note"
]

@app.route('/')
def home():
    selected_project = session.get('project_id', 'oasis')
    project = next((p for p in PROJECTS if p['id'] == selected_project), PROJECTS[0])
    dashboard = {
        "workers": 68,
        "subcontractors": 4,
        "inspections": 3,
        "equipment": 7,
        "pickup_overdue": 2,
        "schedule_behind": 3,
        "specialty_week": 4,
    }
    return render_template('index.html', projects=PROJECTS, project=project, apps=APPS, dashboard=dashboard, quick_actions=QUICK_ACTIONS)

@app.post('/project')
def set_project():
    project_id = request.form.get('project_id', 'oasis')
    if any(p['id'] == project_id for p in PROJECTS):
        session['project_id'] = project_id
    return redirect(url_for('home'))

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
