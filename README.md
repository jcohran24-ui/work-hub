# Field Operations Hub – Version 2

A mobile-first central launcher and administration portal for field applications such as Schedule, Timesheets, Manpower, Equipment, Inspections, Safety, Contacts and future tools.

## Version 2 includes
- Hub username/password login
- Administrator dashboard
- Add/disable projects
- Add/edit/disable work apps without changing code
- User accounts with Field, Superintendent and Administrator roles
- Minimum-role visibility for each app
- Project selector
- PWA manifest/service worker for Add to Home Screen support
- PostgreSQL/Supabase support with a local SQLite fallback
- GitHub + Render deployment files

## Important authentication note
The Hub login controls access to the Hub. It does **not yet** automatically sign the user into each separate existing app. True SSO requires updating those apps to trust the same identity provider. That can be added in a later version.

## Recommended production setup: Supabase
1. Create or open a Supabase project.
2. In Supabase, open **Project Settings → Database** and copy a PostgreSQL connection string suitable for your Render service. Prefer the pooler connection string if direct IPv6 connectivity is unavailable.
3. In Render, create the service from this repository/Blueprint.
4. Set `DATABASE_URL` to the Supabase PostgreSQL connection string.
5. Set `ADMIN_PASSWORD` to a strong initial password.
6. `SECRET_KEY` is generated automatically by Render from `render.yaml`.
7. Deploy.

The app creates its tables automatically. `supabase_schema.sql` is included as a reference if you prefer to create them manually.

## First login
- Username: value of `ADMIN_USERNAME` (default `admin`)
- Password: value you set for `ADMIN_PASSWORD`

If you do not set `ADMIN_PASSWORD`, the development fallback is `ChangeMe123!`. Do not use that fallback on a public deployment.

## Add your existing apps
Sign in as Administrator → **Admin** → **Apps**. Paste the Render URLs for Schedule, Timesheets, Manpower, Equipment and your other tools. No code change is required.

## Run locally
```bash
pip install -r requirements.txt
export ADMIN_PASSWORD='YourStrongPassword'
python app.py
```
Then visit `http://localhost:10000`.

## Database behavior
- If `DATABASE_URL` is present and `psycopg` can connect, the Hub uses PostgreSQL/Supabase.
- Otherwise it uses SQLite at `/tmp/field_hub.db` for local/testing use. Render's `/tmp` storage is not persistent, so use Supabase for production.

## Next integration phase
The dashboard currently shows placeholders for live counts. To populate Workers Onsite, Inspections, Equipment Onsite, Schedule Alerts, etc., connect each existing application's API/database to the Hub. This can be done one app at a time without rebuilding the Hub.
