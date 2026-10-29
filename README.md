# job.zelen.uk

Career tracker backend: Django + DRF + Postgres on the TrueNAS host. System of record for opportunities, communication logs, CVs, notes and goals. The web/mobile app and the agent live in [app.zelen.uk](https://github.com/ozelen/app-zelen-uk) (Cloudflare Workers, Durable Object as BFF) and call this API.

The Obsidian vault `career/` tree is the reference schema; `manage.py import_vault <path>` loads it and can run again.

```bash
cd backend
uv venv && source .venv/bin/activate && uv pip install -r requirements.txt
DJANGO_DB_ENGINE=sqlite DJANGO_SECRET_KEY=dev python manage.py migrate
DJANGO_DB_ENGINE=sqlite DJANGO_SECRET_KEY=dev DJANGO_SUPERUSER_PASSWORD=dev python manage.py seed_superuser
DJANGO_DB_ENGINE=sqlite DJANGO_SECRET_KEY=dev python manage.py import_vault "$VAULT/career"
DJANGO_DB_ENGINE=sqlite DJANGO_SECRET_KEY=dev python manage.py test
```

API: `POST /api/auth/token/`, then `/api/opportunities/`, `/api/people/`, `/api/communications/`, `/api/status-changes/`, `/api/rounds/`, `/api/documents/`, `/api/notes/`, `/api/goals/`, `/api/summary/`. Filter children with `?opportunity=<id>`.

Deploy: push to `main` → tests → `zelenuk/job-api:<sha>` → Jenkins `job-deploy` → `kubectl set image` on `ix-job`. Same pipeline as fin.
