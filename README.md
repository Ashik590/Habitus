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

## Public exercise samples

Exercises use `is_public` to control guest access. Guests can browse the catalog
metadata and practise public samples; other exercises require login for both
the prompt and evaluation API. Signed-in users can access all active exercises
in their native-language direction. List responses never include prompts or
preferred solutions, even for signed-in users.

Migration `d7e9f3a52b01` makes the first two active exercises, ordered by ID, public
within each CEFR level and language pair. It preserves accounts and scores.
New exercises default to `is_public = false`; change individual flags in Supabase
to curate the public samples. This flag is independent of `is_active`.

Catalog exports preserve `is_public`. Older exports without this flag import as
locked exercises, so select their public samples explicitly after import.

For example, after choosing an exercise ID from your catalog:

```sql
-- Replace 42 with the exercise you want to make public.
UPDATE public.exercises SET is_public = true WHERE exercise_id = 42;
-- Use false instead of true to require login again.
```

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
