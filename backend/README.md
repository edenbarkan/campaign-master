# Backend

Flask backend for Campaign Master using the application factory pattern.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and update with your database URL:
```bash
cp .env.example .env
```

4. Run database migrations (configure `DATABASE_URL` to the canonical local SQLite DB `sqlite:///campaign_master.db` from the `backend/` directory):
```bash
export DATABASE_URL=sqlite:///campaign_master.db  # run from backend/
flask db init  # First time only
flask db migrate -m "Initial migration"
FLASK_APP=run.py flask db upgrade
flask db upgrade
```

5. Run the application:
```bash
python run.py
```

The API will be available at `http://localhost:5000`

To verify the SQLite file has all tables/migrations applied:
```bash
export DATABASE_URL=sqlite:///campaign_master.db
python3 -c "import sqlite3, os; path=os.path.abspath('campaign_master.db'); con=sqlite3.connect(path); print(path); print([r[0] for r in con.execute(\"select name from sqlite_master where type='table'\")])"
```

You can also inspect the DB and alembic version via:
```bash
cd backend
chmod +x scripts/db_info.sh  # first time
DATABASE_URL=sqlite:///campaign_master.db ./scripts/db_info.sh
```

## Endpoints

### Health
- `GET /healthz` - Health check endpoint
- `GET /readyz` - Readiness check endpoint (verifies database connection)

### Authentication
- `POST /api/auth/register` - Register a new user
  - Body: `{ "email": "user@example.com", "password": "password", "is_advertiser": true, "is_publisher": false }`
- `POST /api/auth/login` - Login a user
  - Body: `{ "email": "user@example.com", "password": "password" }`
- `POST /api/auth/logout` - Logout the current user (requires authentication)
- `GET /api/auth/me` - Get current user information (requires authentication)

### Wallet
- `GET /api/wallet` - Get current user's wallet information (requires authentication)
  - Returns: `{ "wallet": { "user_id": 1, "balance_micro": 1000000, "reserved_micro": 0, "available_micro": 1000000, "created_at": "..." } }`
- `POST /api/wallet/topup` - Top up wallet balance (requires authentication)
  - Body: `{ "amount_micro": 1000000 }` (optional, defaults to 1,000,000 micro = 1.00)
  - Returns: Updated wallet information

**Note:** All amounts are in micro units (integers). 1,000,000 micro = 1.00 unit.

### Advertiser Endpoints

- `POST /api/advertiser/campaigns` - Create a new campaign (requires authentication)
  - Body: `{ "name": "Campaign Name", "status": "draft", "bid_cpm_micro": 1000000, "bid_cpc_micro": 500000 }`
- `GET /api/advertiser/campaigns` - List all campaigns for current user (requires authentication)
- `PATCH /api/advertiser/campaigns/<id>/status` - Update campaign status (requires ownership)
  - Body: `{ "status": "active" }` (valid: draft, active, paused, archived)
- `POST /api/advertiser/campaigns/<id>/ads` - Create a new ad (requires campaign ownership)
  - Body: `{ "title": "Ad Title", "image_url": "https://...", "landing_url": "https://...", "status": "draft" }`
- `GET /api/advertiser/campaigns/<id>/ads` - List all ads for a campaign (requires campaign ownership)
- `PATCH /api/advertiser/ads/<id>/status` - Update ad status (requires ownership)
  - Body: `{ "status": "active" }` (valid: draft, active, paused, archived)

### Publisher Endpoints

- `POST /api/publisher/sites` - Create a new site (requires authentication)
  - Body: `{ "name": "Site Name", "domain": "example.com" }`
- `GET /api/publisher/sites` - List all sites for current user (requires authentication)
- `PATCH /api/publisher/sites/<id>` - Update site information (requires ownership)
  - Body: `{ "name": "New Name", "domain": "newdomain.com" }`
- `POST /api/publisher/sites/<id>/slots` - Create a new ad slot (requires site ownership)
  - Body: `{ "name": "Slot Name", "width": 300, "height": 250, "floor_cpm_micro": 500000, "floor_cpc_micro": 250000, "status": "active" }`
- `GET /api/publisher/sites/<id>/slots` - List all slots for a site (requires site ownership)
- `PATCH /api/publisher/slots/<id>/status` - Update slot status (requires ownership)
  - Body: `{ "status": "paused" }` (valid: active, paused, archived)

**Authorization:** All endpoints enforce ownership - users can only manage their own resources.

## Testing

Run tests with pytest:

```bash
pytest
```

Or with verbose output:

```bash
pytest -v
```

## Manual verification

Use the verification script to exercise the full advertiser→publisher flow (requires `bash`, `curl`, and `python3`).

```bash
chmod +x backend/scripts/verify_flow.sh
BASE_URL=http://localhost:5001 ./backend/scripts/verify_flow.sh
```

After a successful run the script stores credentials in `backend/tmp/last_users.env`. You can re-use them for quick report checks:

```bash
source backend/tmp/last_users.env
curl -c /tmp/adv.cookies -H 'Content-Type: application/json' \
  -d "{\"email\":\"$ADV_EMAIL\",\"password\":\"$PASSWORD\"}" \
  "$BASE_URL/api/auth/login"
curl -b /tmp/adv.cookies "$BASE_URL/api/reports/advertiser"

curl -c /tmp/pub.cookies -H 'Content-Type: application/json' \
  -d "{\"email\":\"$PUB_EMAIL\",\"password\":\"$PASSWORD\"}" \
  "$BASE_URL/api/auth/login"
curl -b /tmp/pub.cookies "$BASE_URL/api/reports/publisher"
```

## Local development quick start

From the repository root:

```bash
chmod +x backend/scripts/port_kill.sh backend/scripts/dev_reset_db.sh backend/scripts/dev_run.sh
./backend/scripts/port_kill.sh 5001
./backend/scripts/dev_reset_db.sh    # run once or whenever you need a clean DB
./backend/scripts/dev_run.sh
```

In another terminal you can run the verification flow against the dev server:

```bash
BASE_URL=http://localhost:5001 ./backend/scripts/verify_flow.sh
```

## Docker

See `../infra/docker-compose.yml` for running with Docker Compose.
