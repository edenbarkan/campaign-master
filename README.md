# Campaign Master MVP

Production-like AdTech MVP scaffold with Flask, React, Postgres, and Nginx.

## Quick start

```bash
docker compose up -d --build
```

## Demo Quickstart

```bash
make demo
```

Or:

```bash
bash scripts/demo.sh
```

Demo flags:
- `DEMO_SKIP_TESTS=1` skip pytest
- `DEMO_NO_OPEN=1` do not open browser
- `DEMO_OPEN_ALL=0` open only base URL
- `DEMO_PRINT_TOKENS=0` do not print JWT tokens

The demo script prints JWT tokens for all demo users by default.

Demo URLs:
- Base URL: http://localhost:8081
- Buyer: http://localhost:8081/buyer/campaigns
- Partner: http://localhost:8081/partner/get-ad
- Admin: http://localhost:8081/admin/dashboard

Key environment variables (see `.env.example`):
- `PLATFORM_FEE_PERCENT`: platform fee used to compute partner payout (default 30).

Health check:

```bash
curl -i http://localhost:8081/api/health
```

Seed demo data:

```bash
docker compose exec backend python -m app.seed
```

The seed command waits for Postgres readiness (up to ~30s) to avoid connection errors on fresh starts.

Backend runs via Gunicorn (configured in `backend/entrypoint.sh`) for stability.

Demo accounts:
- Buyer: `buyer@demo.com` / `buyerpass`
- Partner: `partner@demo.com` / `partnerpass`
- Admin: `admin@demo.com` / `adminpass`

Manual QA:
- Admin login should land on `/admin/dashboard`.
- Visiting `/partner/dashboard` as admin should redirect to `/admin/dashboard`.

## Reset

```bash
docker compose down -v
```

## Troubleshooting

- Port 80 in use: stop the conflicting service or change the host port in `docker-compose.yml`.
- Default host port is `8081` to avoid collisions with local services.
- Frontend not loading: wait for the `frontend` service to finish building the static bundle.
