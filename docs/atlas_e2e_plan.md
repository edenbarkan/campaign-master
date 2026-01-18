# Atlas Browser E2E Plan

## Global checks
- Log out before switching roles.
- Verify no `undefined`, `null`, or `NaN` is visible in UI labels or metrics.

## Partner flow
1) Login as `partner@demo.com` / `partnerpass`.
2) Confirm "Market Stability Guard" note appears on the Partner dashboard.
3) Toggle Simple/Advanced view; refresh and confirm selection persists.
4) Open "Get Ad" page and request an ad.
5) Confirm "Why this ad?" shows TL;DR bullets in Simple view and full breakdown in Advanced view.
6) Confirm onboarding overlay shows once, then stays dismissed on reload.

## Buyer flow
1) Logout, then login as `buyer@demo.com` / `buyerpass`.
2) Toggle Simple/Advanced view on buyer dashboard; refresh and confirm persistence.
3) Verify campaign form shows partner payout estimate + remaining budget.
4) Confirm status helper text is visible and clear.
5) Confirm onboarding overlay shows once, then stays dismissed.

## Admin flow
1) Logout, then login as `admin@demo.com` / `adminpass`.
2) Use 7d/30d/90d filter; ensure totals and charts update without errors.
3) Click a reject reason row and verify the detail panel shows guidance text.
4) Confirm onboarding overlay shows once, then stays dismissed.
