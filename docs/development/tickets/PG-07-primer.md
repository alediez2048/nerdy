# PG-07 Primer: Frontend User Context and Token Expiry Handling

**For:** New Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** April 2026
**Previous work:** P0-P5, PA-PD complete. PG-01 must be done first.

---

## What Is This Ticket?

The frontend sends Clerk JWTs but never extracts the current user's identity programmatically. There's no handling for expired sessions, and campaign types don't include `user_id`. This ticket adds user context to the frontend and handles auth edge cases.

### Current Gaps
1. **No user context in API module** — `api/auth.ts` can get tokens but not user info (ID, email)
2. **Campaign types missing user_id** — `CampaignSummary` and `CampaignDetail` in `types/campaign.ts` don't include `user_id` (session types do)
3. **No token expiry handling** — if Clerk session expires, API calls silently fail with 401
4. **No error boundary for auth failures** — failed API calls show generic "Failed to fetch" instead of "Session expired, please sign in"

---

## What This Ticket Must Accomplish

### Goal
Add user context, type consistency, and auth error handling to the frontend.

### Deliverables Checklist

#### A. Implementation

- [ ] **Add user context to `api/auth.ts`:**
  - Export `getCurrentUserId(): string | null` using Clerk's `useUser()` hook or by decoding the cached JWT
  - This lets components verify ownership client-side before making destructive API calls

- [ ] **Update `types/campaign.ts`:**
  - Add `user_id: string` to `CampaignSummary` type
  - Add `user_id: string` to `CampaignDetail` type
  - Backend already has user_id on the model — update Pydantic schema to include it in response

- [ ] **Update backend campaign schemas** (`app/api/schemas/campaign.py`):
  - Add `user_id: str` to `CampaignSummary` and `CampaignDetail` response models
  - Update route handlers to include `user_id` in response construction

- [ ] **Add auth error interceptor:**
  - In `api/sessions.ts` and `api/campaigns.ts`, detect 401 responses in `handleResponse()`
  - On 401: clear cached token, trigger Clerk sign-in modal or redirect
  - Show toast/banner: "Session expired — please sign in again"

- [ ] **Add token refresh error handling** in `api/auth.ts`:
  - If `_clerkGetToken()` returns null during refresh, update a reactive state
  - Components can check auth state before rendering protected content

#### B. Testing

- [ ] Verify campaign list/detail responses include `user_id` field
- [ ] Verify expired token triggers sign-in flow (not silent failure)
- [ ] Verify `getCurrentUserId()` returns correct Clerk user ID

---

## Key Files

| File | Action |
|------|--------|
| `app/frontend/src/api/auth.ts` | Add `getCurrentUserId()`, token expiry handling |
| `app/frontend/src/types/campaign.ts` | Add `user_id` field |
| `app/frontend/src/api/sessions.ts` | Add 401 interceptor |
| `app/frontend/src/api/campaigns.ts` | Add 401 interceptor |
| `app/api/schemas/campaign.py` | Add `user_id` to response schemas |
| `app/api/routes/campaigns.py` | Include `user_id` in response construction |
