# Deploy Habitus v0.1.0

Target: a free Render Docker web service, with Supabase PostgreSQL and Storage.
Hosting limits and provider allowances apply. Use only the Free plans; no custom
domain is needed. Gemini API access and quotas are configured separately.

## 1. Create Supabase resources

Create a Free project at https://supabase.com/dashboard.

- Under **Connect**, copy the **Session pooler** PostgreSQL URI (port 5432),
  which works with IPv4 hosting. Insert your database password, URL-encoding
  reserved characters in the password.
- Change the URI scheme from `postgresql://` to `postgresql+psycopg://` and add
  `?sslmode=require` (or `&sslmode=require` if a query already exists).
- Under **Storage**, create a **public** bucket named `profile-pictures`.
  Set its maximum file size to 5 MB and allowed MIME types to `image/jpeg`,
  `image/png`, and `image/webp`. Public means pictures are publicly viewable.
  Do not add anonymous upload/delete policies; writes go through the backend.
- Under project API settings, copy the project URL and backend **service_role**
  key. This key is private: store it only in backend environment variables.
  Never use a `VITE_` variable for it or commit it to GitHub.

## 2. Verify the code locally

Run from the repository root:

```bash
cd frontend
npm ci
npm run build
npm run lint
cd ../backend
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m compileall -q app
.venv/bin/alembic heads
cd ..
git diff --check
git status --short
```

Dependency pins were read from the development virtual environment, not tested
in a clean container yet. Resolve any installation/build failure before release.

## 3. Create the hosted schema and copy exercises

Migration `c6d8e2f41a90` deletes existing accounts and their saved exercise scores
as part of the authorized account reset. It keeps exercises and languages.
Review this migration before running `upgrade head` or deploying: Docker startup
also applies pending migrations automatically. Deleted account data cannot be
restored by downgrading. Existing users must register again with a username and
target language after this migration.

Create `backend/.env.production` in your editor (it is Git-ignored):

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@SESSION_POOLER_HOST:5432/postgres?sslmode=require
JWT_SECRET_KEY=replace_with_a_random_secret
```

Keep `backend/.env` pointing at your local database. Export the local catalog:

```bash
cd backend
.venv/bin/python -m app.catalog_transfer export catalog-export.json
```

Create the hosted tables using the production connection, without changing the
local `.env`. This command intentionally creates/updates the remote schema:

```bash
.venv/bin/python -c 'from app.core.config import Settings; from alembic.config import Config; from alembic import command; import os; os.environ["DATABASE_URL"] = Settings(_env_file=".env.production").database_url; command.upgrade(Config("alembic.ini"), "head")'
.venv/bin/python -m app.catalog_transfer import catalog-export.json --env-file .env.production
cd ..
```

The import copies languages and exercises, never users or scores. It refuses to
import into a database that already contains exercises. The export file must
not already exist; use a different filename for a subsequent export.

In Supabase SQL Editor, enable RLS on application tables to prevent direct
browser access through Supabase's Data API. Habitus connects server-side using
the database owner and continues to work:

```sql
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_exercises ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.languages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exercises ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY;
```

## 4. Commit and push manually

Review `git status --short` and `git diff`. Include the deployment files and any
earlier feature changes you intend to release. Commit them yourself, then run:

```bash
git push origin main
```

Do not include `.env`, `.env.production`, uploads, or catalog exports.

## 5. Deploy Render Blueprint

Open https://dashboard.render.com/select-repo?type=blueprint and connect
https://github.com/Ashik590/Habitus. Use `render.yaml` on `main`.
Confirm the service plan is **Free** before creating it.

Supply these environment variables when prompted:

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | The Supabase session-pooler URI from step 1 |
| `GEMINI_API_KEY` | Your Gemini API key |
| `SUPABASE_URL` | `https://YOUR_PROJECT.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend-only service_role key |
| `FRONTEND_ORIGIN` | Your Render HTTPS origin, without a trailing slash |

If you do not yet know the service URL, use `https://example.invalid` as the
initial origin, then replace it with the assigned Render URL and redeploy.
The built frontend calls the API on the same origin, so it does not depend on
CORS for its initial load. The blueprint generates the JWT secret and enables
secure refresh cookies automatically.

Docker builds the frontend and installs backend dependencies. Gemini transcribes
and evaluates the recording directly, without browser transcripts or preferred
solutions from the database.
No Whisper model is downloaded or loaded on the server. Remove obsolete
`WHISPER_MODEL` and `HF_HUB_OFFLINE` variables from Render if present.
Startup applies migrations, then starts one Uvicorn worker. No separate
frontend service, build command, start command, or paid pre-deploy job is needed.

## 6. Verify the live service

- Open the assigned HTTPS URL and visit `/profile` directly.
- Check `/api/v1/health` and `/api/v1/health/database`.
- Register, log in, reload, and confirm the session persists.
- Confirm the transferred exercises appear and submit a recording.
- Confirm the dashboard reflects the result.
- Upload a picture, redeploy, and confirm the picture survives; test removal.
- Watch Render logs and memory during the first and subsequent evaluations.

Render Free has 512 MB RAM and sleeps after inactivity. Whether this backend
fits must be established by a live evaluation. If it exits with an out-of-memory
error, keep this as a release candidate and change the hosting/inference setup
before declaring the deployment successful. Do not enable a paid plan silently.

## 7. Publish the first GitHub Release

Only after the live checks pass, publish release notes for the verified commit.
On GitHub, open **Releases → Draft a new release**:

- Create tag `v0.1.0` against the verified deployment commit.
- Title: `Habitus v0.1.0`.
- Describe the features, changes, and known limitations in the release notes.
- Add your live site URL and publish the release.

Reference documentation:
- https://render.com/docs/blueprint-spec
- https://render.com/docs/free
- https://supabase.com/docs/guides/database/connecting-to-postgres
- https://supabase.com/docs/guides/storage/buckets/creating-buckets
