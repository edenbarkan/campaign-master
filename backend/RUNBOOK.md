# Runbook

## Swagger smoke checklist
1. Start the backend (e.g. `PG_PORT=55432 ./scripts/dev_pg.sh`) and open http://localhost:5001/docs.
2. Use **POST /api/auth/register** and **POST /api/auth/login** in Swagger to create/log in advertiser + publisher accounts. Swagger will store the session cookie (cookieAuth).
3. As the advertiser, call **POST /api/wallet/topup**, **POST /api/advertiser/campaigns**, and **POST /api/advertiser/campaigns/{id}/ads** with the provided JSON examples.
4. As the publisher, create a site and slot via **POST /api/publisher/sites** and **POST /api/publisher/sites/{id}/slots**.
5. Hit **GET /api/adserve** with the new `slot_id`, then track via **GET /api/track/impression** and **GET /api/track/click**.
6. Finally, verify spend/earn totals through **GET /api/reports/advertiser** and **GET /api/reports/publisher**—both should reflect the recorded events.
