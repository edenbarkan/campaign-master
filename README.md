# Campaign Master MVP

Production-like AdTech MVP scaffold with Flask, React, Postgres, and Nginx.

## Quick start

```bash
docker compose up -d --build
```

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
