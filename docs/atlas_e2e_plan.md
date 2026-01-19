# Atlas Browser E2E Plan

## Global checks
- Log out before switching roles.
- Verify no `undefined`, `null`, or `NaN` is visible in UI labels or metrics.
- Confirm active Simple/Advanced toggle styling is visibly selected.
- Confirm the onboarding nudge banner appears on first login per role and stays dismissed after reload.
- Confirm dashboards show “Updated Xs ago” and the Refresh button updates the timestamp.
- Confirm Login page shows value prop and trust bullets (accepted-only billing, ranking-only scoring, transparent payouts).
- In split-view (~50% width), confirm primary CTAs remain visible for Buyer campaign create and Partner Get Ad.

## Partner flow
1) Login as `partner@demo.com` / `partnerpass`.
2) Confirm "Market Stability Guard" note appears on the Partner dashboard.
3) Toggle Simple/Advanced view; refresh and confirm selection persists.
4) Open "Get Ad" page and request an ad.
5) Confirm "Why this ad?" shows TL;DR bullets by default and details are expandable.
6) Hover "Record impression" and "Test click" to confirm tooltips appear.
7) Hover KPI info icons on Partner dashboard (Earnings, CTR, EPC, Fill rate, Requests).
8) Hover the Partner filter labels or info icons to confirm tooltips appear (inline helper text is also acceptable).
9) If the ad image is blocked, verify the preview fallback card renders with title/body/domain.
10) Use the header "How it works" link, then click "Restart onboarding" and confirm the nudge reappears on dashboard.
11) Confirm the onboarding nudge banner shows once, then stays dismissed on reload.

## Buyer flow
1) Logout, then login as `buyer@demo.com` / `buyerpass`.
2) Toggle Simple/Advanced view on buyer dashboard; refresh and confirm persistence.
3) Verify campaign form shows partner payout estimate + remaining budget.
4) Confirm Effective CPC, Fill rate, Cost efficiency, and CTR labels show tooltips.
5) Confirm status helper text is visible and clear; date fields show “coming soon” and are disabled.
6) Confirm chart legends and axis labels are visible in Spend/Clicks charts.
7) Use the header "How it works" link, then click "Restart onboarding" and confirm the nudge reappears on dashboard.
8) Confirm the onboarding nudge banner shows once, then stays dismissed.
9) If no campaigns exist, confirm the empty state CTA prompts creation.

## Admin flow
1) Logout, then login as `admin@demo.com` / `adminpass`.
2) Use 7d/30d/90d filter; ensure totals and charts update without errors.
3) Hover the date presets and reject reason rows to confirm tooltips appear.
4) Confirm chart legends and axis labels are visible in the trend charts.
5) Click a reject reason row and verify the detail panel shows meaning, cause, and mitigation text.
6) Use the header "How it works" link, then click "Restart onboarding" and confirm the nudge reappears on dashboard.
7) Confirm the onboarding nudge banner shows once, then stays dismissed.
8) If no data in range, confirm the empty state guidance appears.
