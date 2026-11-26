# Habitus

Habitus is a learning project by Md Azizul Hakim, originating in Dhaka,
Bangladesh. Practise spoken translations with timed exercises, speech
transcription, AI feedback, and a personal learning dashboard.

Stack: React, TypeScript, Vite, FastAPI, PostgreSQL, and Gemini.

The browser records audio without producing a transcript. The backend sends
the recording, source sentence, language direction, CEFR level, and scoring
instructions to Gemini. A temporary server failure or network timeout permits
one automatic retry (at most two attempts using the same API key). Invalid
requests, authentication errors, and rate-limit responses are not retried.
Preferred solutions from the database
are not included. Gemini transcribes the audible response and evaluates it;
recommended translations are generated independently from the source sentence.
Neither Whisper nor browser speech recognition is used.

## Accounts and practice preferences

Signup requires a full name, unique username, password, native language, and
target language. Email is optional; supplied addresses must be valid and unique.
Usernames use 3–30 English letters, numbers, or underscores, start with a letter,
and are stored in lowercase. Login requires a username and password.

Signed-in visitors to `/practice` go directly to exercises for their saved
language pair. Guests retain the language picker. The dashboard saves target
language changes; choosing the saved target as a new native language swaps the
pair in one update.

Migration `c6d8e2f41a90` intentionally resets existing accounts: it deletes all
users and their saved scores before introducing the required fields. This reset
was chosen for the learning project. Exercise content and languages are retained;
deleted account data cannot be restored by downgrading the migration.

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

See [GitHub Releases](https://github.com/Ashik590/Habitus/releases) for version
history, release notes, and known limitations.

## Checks

```bash
cd frontend
npm run build
npm run lint
```

```bash
cd backend
.venv/bin/python -m compileall -q app
.venv/bin/python -m unittest discover -s tests -v
```

Deployment checks: register, log in, refresh the page, upload and remove a
profile picture, submit an exercise, and verify its score in the dashboard.
Visit `/profile` directly to check React routing. Check `/api/v1/health/database`
to confirm database connectivity. These commands and checks must be run by the
developer before publishing a release.
