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
- `FREQ_CAP_SECONDS`: frequency cap window per partner/ad (default 60).
- `MATCH_CTR_LOOKBACK_DAYS`: CTR history lookback window (default 14).
- `MATCH_REJECT_LOOKBACK_DAYS`: reject-rate lookback window (default 7).
- `MATCH_CTR_WEIGHT`: CTR weight in matching score (default 1.0).
- `MATCH_TARGETING_BONUS`: bonus per targeting match (default 0.5).
- `MATCH_REJECT_PENALTY_WEIGHT`: reject-rate penalty weight (default 1.0).

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

## Matching v2 notes

- Partner ad requests are tracked (filled vs unfilled) to compute fill-rate.
- Frequency capping prevents the same ad from returning to the same partner within the cap window.
- Match responses include `explanation` and `score_breakdown` for transparency.
- Partner requests use `GET /api/partner/ad` with optional query params: `category`, `geo`, `placement`, `device`.
- `partner_reject_penalty` in score breakdown is derived from the partner's reject rate (partner quality), not the ad itself.
- Reject rate window: last `MATCH_REJECT_LOOKBACK_DAYS` days (default 7).
- Reject penalty formula: `partner_reject_penalty = partner_reject_rate * MATCH_REJECT_PENALTY_WEIGHT` (default weight 1.0).
- Quality penalty applied to the score: `partner_quality_penalty = partner_reject_penalty * delta_quality`.
- `partner_reject_rate` is computed from click decision events only (accepted + rejected clicks) within the lookback window — impressions are not included in this calculation.

## Iteration 4: Adaptive matching + marketplace intelligence

- Adaptive score formula: `profit * alpha_profit + ctr * beta_ctr + targeting_bonus * gamma_targeting - partner_quality_penalty * delta_quality`.
- Adaptive multipliers (`alpha_profit`, `beta_ctr`, `gamma_targeting`, `delta_quality`) are derived from a runtime market health snapshot.
- Partner quality lifecycle states: `NEW`, `STABLE`, `RISKY`, `RECOVERING` (state affects `delta_quality` only).
- Controlled exploration adds a small, capped bonus for new partners or new ads (`exploration_applied`, `exploration_bonus`).
- Delivery balancing adds a temporary boost for under-delivering campaigns (`delivery_boost`).
- `score_breakdown` includes multipliers, `partner_quality_state`, `exploration_applied`, and `delivery_boost`.

Key env knobs:
- Market health: `MARKET_HEALTH_*`, `ALPHA_PROFIT_BOOST_*`, `BETA_CTR_BOOST_HEALTHY`, `GAMMA_TARGETING_BOOST_*`, `DELTA_QUALITY_BOOST_*`.
- Partner quality: `PARTNER_QUALITY_*`.
- Exploration: `EXPLORATION_*`.
- Delivery balancing: `DELIVERY_*`.

## Iteration 5: UX hardening controls

- Simple/Advanced view toggles for Buyer and Partner pages (persisted in localStorage).
- Tab-style toggle with helper hint for Simple vs Advanced views.
- Role-based onboarding overlay (dismissed once per role).
- "Market Stability Guard" note clarifies scoring is rank-only.
- Partner quality badge highlights state with tooltip guidance.
- Admin 7d/30d/90d date range filter + reject-reason drill-down panel.
- "How it works" pages are linked in each role header (Buyer/Partner/Admin) with glossary + FAQs.
- "How it works" pages include quick action CTAs, plus a partner template helper.

Atlas E2E plan: `docs/atlas_e2e_plan.md`.

## Demo script (fast walkthrough)

1) Login as buyer → `http://localhost:8081/buyer/dashboard`.
2) Toggle Simple/Advanced, confirm persistence on refresh.
3) Open a campaign and show partner payout + remaining budget helper.
4) Logout, then login as partner → `http://localhost:8081/partner/dashboard`.
5) Request an ad; show TL;DR vs Advanced "Why this ad?" breakdown.
6) Logout, then login as admin → `http://localhost:8081/admin/dashboard`.
7) Click 7d/30d/90d filters and open a reject reason detail panel.

Always logout before switching roles.

## What changed / How to verify manually

- Buyer: toggle Simple/Advanced tabs on the dashboard and confirm the hint text and advanced KPIs (budget left, max CPC, clicks) appear; open "How it works" and use the CTA links.
- Login: confirm value prop and trust bullets are visible above the form.
- Buyer: verify the onboarding nudge banner appears once and can be restarted from "How it works"; check chart legends/axis labels and tooltips for Effective CPC, Fill rate, Cost efficiency, CTR; confirm date fields show “coming soon”.
- Partner: confirm the quality badge styling and tooltips, open "Get Ad" and verify filter tooltips plus "Record impression" / "Test click" tooltips; confirm preview fallback renders if an image is blocked and copy snippet works; restart onboarding from "How it works".
- Admin: switch date presets, click a reject reason to open the detail panel, verify "Updated Xs ago" and refresh, and ensure chart legends/axis labels are visible; restart onboarding from "How it works".

## Reject penalty verification

```bash
bash scripts/verify_reject_penalty.sh
```

Notes:
- The script runs `make demo` with `MATCHING_DEBUG=1` and `FREQ_CAP_SECONDS=0` unless `VERIFY_SKIP_DEMO=1` is set.
- It creates a temporary buyer + partner, requests an ad, forces a duplicate-click rejection, and asserts the penalty update.

## Reset

```bash
docker compose down -v
```

## Troubleshooting

- Port 80 in use: stop the conflicting service or change the host port in `docker-compose.yml`.
- Default host port is `8081` to avoid collisions with local services.
- Frontend not loading: wait for the `frontend` service to finish building the static bundle.
