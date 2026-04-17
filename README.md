# YouTube Agent OS

YouTube Agent OS is a Python application for assisted YouTube video production.

It combines content generation, media preparation, rendering, human review, private upload, publication, and basic analytics in one workflow. The goal is simple: reduce the operational friction between an idea and a publishable YouTube video.

## Why this project exists

Publishing a video usually means jumping across too many tools:

- one place for ideas
- another for scripts
- another for thumbnails
- another for rendering
- another for upload and review

This project brings that flow together in a single local system with a clean architecture and room to evolve from deterministic local adapters into real AI-powered media providers.

## What it does today

The current version already supports:

- YouTube OAuth 2.0 connection
- project creation from a base idea
- generation of briefing, script, title, description, tags, and production plan
- preparation of media assets
- video rendering
- human review before publication
- private upload to YouTube
- public publishing and scheduling
- basic analytics collection
- a simple operational timeline for the project
- a configuration screen to manage environment settings from the UI

## Product flow

1. Connect a YouTube channel
2. Configure the system
3. Create a project from a base idea
4. Generate content
5. Prepare assets
6. Render the video
7. Review everything with a human in the loop
8. Upload as `private`
9. Publish immediately or schedule publication
10. Collect analytics

## Main interfaces

### Studio

The Studio is the entry point for the workflow.

URL:

```text
http://localhost:8000/api/v1/studio
```

From there, you can:

- select a connected channel
- create and prepare a project
- jump to system configuration

### System settings

The system settings page lets you fill the main environment values without editing `.env` manually.

URL:

```text
http://localhost:8000/api/v1/system/settings
```

It covers:

- application settings
- infrastructure settings
- YouTube OAuth credentials
- media and AI providers

### Review dashboard

The review dashboard is the operational control panel for each project.

URL pattern:

```text
http://localhost:8000/api/v1/review/projects/{project_id}
```

From there, you can:

- preview rendered video and thumbnail
- inspect generated metadata
- approve or reject
- upload privately
- publish or schedule
- inspect operational events

## Architecture

```text
app/
  api/          # FastAPI routes and server-rendered UI
  adapters/     # provider integrations and concrete implementations
  core/         # configuration, security, shared infrastructure
  db/           # models, repositories, database session
  domain/       # enums and domain rules
  services/     # application use cases
  tasks/        # Celery background tasks
alembic/        # migrations
tests/          # automated test suite
```

Design principles:

- domain and business flow are kept separate from frameworks
- external services are isolated behind adapters
- human approval remains part of the publishing pipeline
- secrets are configuration-driven
- the system is usable locally without production infrastructure

## Tech stack

- Python 3.12
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- Celery
- FFmpeg
- Agno
- Google APIs / OAuth

## Running locally

### 1. Start PostgreSQL and Redis

```powershell
docker compose up db redis -d
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .[dev]
```

### 3. Create your `.env`

```powershell
Copy-Item .env.example .env
```

For a local Windows setup with Docker only for database and Redis, a common configuration is:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:55432/youtube_agent_os
REDIS_URL=redis://localhost:6379/0
```

At minimum, you should fill:

- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `YOUTUBE_OAUTH_CLIENT_ID`
- `YOUTUBE_OAUTH_CLIENT_SECRET`
- `YOUTUBE_OAUTH_REDIRECT_URI`

### 4. Apply migrations

```powershell
python -m alembic upgrade head
```

### 5. Start the API

```powershell
python -m uvicorn app.main:app --reload
```

### 6. Start the worker

In another terminal:

```powershell
.venv\Scripts\Activate.ps1
python -m celery -A app.tasks.celery_app.celery_app worker -l info -Q pipeline
```

## Running with Docker

```powershell
docker compose up --build
```

Services included:

- `api`
- `worker`
- `db`
- `redis`

## Useful commands

```bash
make install
make format
make lint
make typecheck
make test
make run
make run-worker
make alembic-upgrade
make docker-up
make docker-down
```

## YouTube OAuth setup

The application uses official Google OAuth 2.0 for YouTube.

Typical setup:

1. create a Google Cloud project
2. enable YouTube Data API v3
3. configure the OAuth consent screen
4. create a `Web application` OAuth client
5. register this exact redirect URI:

```text
http://localhost:8000/api/v1/oauth/youtube/callback
```

Then open:

```text
http://localhost:8000/api/v1/oauth/youtube/authorize
```

## Media providers

### Local development mode

This is the cheapest and easiest mode for local development:

```env
THUMBNAIL_PROVIDER=deterministic
VIDEO_PROVIDER=ffmpeg
TTS_PROVIDER=edge_tts
TTS_VOICE_NAME=pt-BR-AntonioNeural
TTS_RATE=0
```

### Google Cloud / Vertex AI mode

For more advanced media generation:

```env
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_CLOUD_LOCATION=us-central1
THUMBNAIL_PROVIDER=vertex_imagen
VIDEO_PROVIDER=vertex_veo
VERTEX_IMAGEN_MODEL=imagen-4.0-fast-generate-001
VERTEX_VEO_MODEL=veo-3.0-fast-generate-001
VERTEX_VEO_ASPECT_RATIO=16:9
VERTEX_VEO_RESOLUTION=720p
VERTEX_VEO_DURATION_SECONDS=8
VERTEX_VEO_GENERATE_AUDIO=true
TTS_PROVIDER=google_cloud
GOOGLE_TTS_VOICE_NAME=pt-BR-Chirp3-HD-Achernar
GOOGLE_TTS_LANGUAGE_CODE=pt-BR
GOOGLE_TTS_SPEAKING_RATE=1.0
```

Notes:

- ADC must be configured
- billing must be active in Google Cloud
- Imagen, Veo, and Google TTS generate real cost

## Quality checks

The project includes:

- `ruff`
- `mypy`
- `pytest`

Latest local validation for this version:

- `57 passed`
- `mypy` clean
- `ruff` clean

## Security notes

Before making the repository public:

- never commit `.env`
- never expose client secrets, tokens, or internal keys
- rotate any credential that may have been exposed during development
- review local shell history if sensitive values were typed manually

## Current status

This is already a functional MVP, not just a code sketch.

It still has room to evolve in areas like:

- operator authentication
- external asset storage
- richer observability
- deeper analytics history
- staging and production deployment
- more cost-efficient generative media strategies

## License

This project is released under the MIT License. See [`LICENSE`](LICENSE).
