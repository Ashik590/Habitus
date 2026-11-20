# Habitus

Habitus is a learning project by Md Azizul Hakim, originating in Dhaka,
Bangladesh. Practise spoken translations with timed exercises, speech
transcription, AI feedback, and a personal learning dashboard.

Stack: React, TypeScript, Vite, FastAPI, PostgreSQL, Faster Whisper, and Gemini.

## Development

Use Python 3.12, Node.js 24, and PostgreSQL. From the repository root:

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` with your database URL, a random JWT secret, and Gemini key.
Generate a secret locally with `openssl rand -hex 32`. Never commit credentials.

```bash
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

In a second terminal, from the repository root:

```bash
cd frontend
npm ci
npm run dev
```

The frontend runs at http://localhost:5173; API documentation is at
http://localhost:8000/docs. Migrations populate languages, but the exercise
catalog must be imported separately. See the deployment guide for transferring
an existing catalog.

## Deployment and release

Follow [DEPLOYMENT.md](DEPLOYMENT.md). The root Dockerfile builds React and serves
it through FastAPI on the same origin. `render.yaml` selects a free Render
service. PostgreSQL and profile pictures use a separately configured Supabase
project. Existing account authentication remains managed by Habitus.

See [CHANGELOG.md](CHANGELOG.md) for the first release candidate and limitations.

## Checks

```bash
cd frontend
npm run build
npm run lint
```

```bash
cd backend
.venv/bin/python -m compileall -q app
```

Deployment checks: register, log in, refresh the page, upload and remove a
profile picture, submit an exercise, and verify its score in the dashboard.
Visit `/profile` directly to check React routing. Check `/api/v1/health/database`
to confirm database connectivity. These commands and checks must be run by the
developer before publishing a release.
