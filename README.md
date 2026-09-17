# Field Operations Hub — No Login Version

A mobile-first central dashboard for launching and managing work apps from one place.

## Important change

**There is no sign-in to the Hub.** Opening the Hub URL goes directly to the dashboard.

Each linked app can still use its own login, PIN, or permissions if that app requires them.

## Included

- Direct-to-dashboard home page
- Project selector
- Work app cards
- Quick Action launcher
- Manage Hub page at `/admin`
- Add/edit/disable projects
- Add/edit/disable/reorder app links
- Supabase/PostgreSQL support
- SQLite fallback
- PWA manifest/service worker
- GitHub + Render deployment files

## Deploy on Render

1. Upload the project files to GitHub.
2. In Render choose **New → Blueprint**.
3. Connect the GitHub repository.
4. Render reads `render.yaml` and deploys the Flask app.
5. Open the Render URL. The dashboard opens immediately with no Hub login.

## App URLs

You can configure initial links with environment variables:

- `SCHEDULE_URL`
- `TIMESHEETS_URL`
- `MANPOWER_URL`
- `EQUIPMENT_URL`
- `SPECIALTY_URL`
- `INSPECTIONS_URL`
- `SAFETY_URL`
- `CONTACTS_URL`
- `DOCUMENTS_URL`

After the database is seeded, use **Manage Hub** on the dashboard to edit links without changing code.

## Database

Set `DATABASE_URL` to a PostgreSQL/Supabase connection string for persistent production data. Without it, the app uses `/tmp/field_hub.db`, which is useful for testing but may reset on Render restarts.

## Security note

Because the Hub intentionally has no authentication, anyone who can reach the Hub URL can also reach the **Manage Hub** page and change Hub configuration. The linked apps remain responsible for their own authentication/security.

If desired later, the dashboard can remain login-free while protecting only the Manage Hub page with a simple admin PIN.


## V4 cleanup
Removed Safety, Contacts, Documents, Specialty Subs, and Inspections from the hub. Existing database rows for these modules are automatically removed on startup.
