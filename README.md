# Campaign Master MVP

Production-like AdTech MVP scaffold with Flask, React, Postgres, and Nginx.

## Quick start

```bash
docker compose up -d --build
```

Health check:

```bash
curl -i http://localhost:8081/api/health
```

Seed demo data:

```bash
docker compose exec backend python -m app.seed
```

## Reset

```bash
docker compose down -v
```

## Troubleshooting

- Port 80 in use: stop the conflicting service or change the host port in `docker-compose.yml`.
- Default host port is `8081` to avoid collisions with local services.
- Frontend not loading: wait for the `frontend` service to finish building the static bundle.
