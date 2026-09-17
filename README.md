# Field Operations Hub

A mobile-first central dashboard for construction field apps.

## Included
- Project selector
- Superintendent dashboard cards
- App launcher cards
- Quick Add menu
- PWA manifest/service worker
- GitHub + Render ready
- Environment-variable app links

## Local Run
```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```
Open http://localhost:10000

## Render Deployment
1. Push this folder to a GitHub repository.
2. In Render choose **New > Blueprint** and connect the repository.
3. Render will read `render.yaml`.
4. Add your existing app URLs in the Render Environment page:
   - `SCHEDULE_URL`
   - `TIMESHEETS_URL`
   - `MANPOWER_URL`
   - `EQUIPMENT_URL`
   - `SPECIALTY_URL`
   - `INSPECTIONS_URL`
   - `SAFETY_URL`
   - `CONTACTS_URL`
   - `DOCUMENTS_URL`
5. Redeploy.

## Recommended Next Version
- User login and roles
- Supabase project/app configuration
- Live dashboard metrics from each app
- Unified notifications / overdue items
- One project selector shared across apps
- Admin page to add/edit app links without Render environment variables
