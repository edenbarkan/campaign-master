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
- `CLICK_HASH_SALT`: salt for hashing IP/user agent fingerprints.
- `CLICK_DUPLICATE_WINDOW_SECONDS`: duplicate click rejection window (default 10).
- `CLICK_RATE_LIMIT_PER_MINUTE`: per-IP click rate limit (default 20/min).
- `IMPRESSION_DEDUP_WINDOW_SECONDS`: impression dedup window (default 60).

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
- Double-clicking the same tracking URL within 10 seconds should show up as a rejected click in admin risk analytics.

## Smoke demo

```bash
make smoke
```

Optional flags:
- `SMOKE_SKIP_DEMO=1` skip running `make demo` inside the smoke script.
- `BASE_URL=http://localhost:8081` override the base URL.

The smoke script validates spend/earnings deltas and rejects a duplicate click.

## Click validation and rejection reasons

The click validator records every click with an ACCEPTED or REJECTED status. Rejections are stored with a reason:
- `DUPLICATE_CLICK` repeated click from the same IP within the duplicate window.
- `RATE_LIMIT` too many clicks from the same IP per minute.
- `BUDGET_EXHAUSTED` campaign cannot cover the max CPC and is paused.
- `INVALID_ASSIGNMENT` missing or invalid assignment code.
- `BOT_SUSPECTED` empty user-agent string.

## Reset

```bash
docker compose down -v
```

## Troubleshooting

- Port 80 in use: stop the conflicting service or change the host port in `docker-compose.yml`.
- Default host port is `8081` to avoid collisions with local services.
- Frontend not loading: wait for the `frontend` service to finish building the static bundle.
