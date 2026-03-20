# PC-10 Primer: Navigation Update — Home → Campaigns + Breadcrumbs

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PC-06 (CampaignList), PC-07 (NewCampaignForm), PC-08 (CampaignDetail), PC-09 (Session pre-fill). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PC-10 restructures the app navigation so campaigns are the primary entry point. The home page (`/`) redirects to `/campaigns` instead of `/sessions`. A persistent nav bar or breadcrumb system ties the hierarchy together: Campaigns → Campaign Detail → Session Detail. The flat `/sessions` view remains accessible but becomes secondary.

### Why It Matters

- Campaigns are now the top-level organizing concept — navigation should reflect that
- Users coming from `/sessions/new` or deep links need clear wayfinding
- Breadcrumbs prevent users from getting lost in the Campaign → Session → Tab hierarchy
- The flat sessions view is still useful for power users who want to see everything

---

## What Was Already Done

- PC-06: `CampaignList` at `/campaigns`
- PC-08: `CampaignDetail` at `/campaigns/:campaignId`
- PA-06: `SessionList` at `/sessions`
- PA-09: `SessionDetail` at `/sessions/:sessionId`
- `App.tsx`: current routes with `/` → `/sessions` redirect

---

## What This Ticket Must Accomplish

### Goal

Update navigation so `/` → `/campaigns`, add a persistent navigation bar, and implement breadcrumbs across all views.

### Deliverables Checklist

#### A. Route Update (`app/frontend/src/App.tsx` — modify)

- [ ] Change default redirect: `/` → `/campaigns`
- [ ] All routes:
  - `/campaigns` — CampaignList
  - `/campaigns/new` — NewCampaignForm
  - `/campaigns/:campaignId` — CampaignDetail
  - `/campaigns/:campaignId/sessions/new` — NewSessionForm (with campaign context)
  - `/sessions` — SessionList (flat view, all sessions)
  - `/sessions/new` — NewSessionForm (standalone)
  - `/sessions/:sessionId` — SessionDetail
  - `/sessions/:sessionId/live` — WatchLive
  - `/shared/:token` — SharedSession
  - `/dashboard` — GlobalDashboard

#### B. Navigation Bar (`app/frontend/src/components/NavBar.tsx` — create)

- [ ] Persistent top bar (replaces floating logo + theme toggle)
- [ ] Left: Nerdy logo (links to `/campaigns`)
- [ ] Center/left: nav links — Campaigns, All Sessions, Dashboard
- [ ] Right: Theme toggle (light/dark)
- [ ] Active link indicator (underline or highlight)
- [ ] Responsive: collapses gracefully on small screens
- [ ] Consistent with existing design tokens

#### C. Breadcrumbs (`app/frontend/src/components/Breadcrumbs.tsx` — create)

- [ ] Reusable breadcrumb component
- [ ] Input: array of `{ label: string, path?: string }` items
- [ ] Last item is current page (not a link)
- [ ] Styling: subtle, above page content, consistent with design tokens
- [ ] Usage across views:
  - CampaignDetail: `Campaigns / [Campaign Name]`
  - SessionDetail (from campaign): `Campaigns / [Campaign Name] / [Session Name]`
  - SessionDetail (standalone): `Sessions / [Session Name]`
  - NewSessionForm (from campaign): `Campaigns / [Campaign Name] / New Session`
  - NewSessionForm (standalone): `Sessions / New Session`
  - NewCampaignForm: `Campaigns / New Campaign`

#### D. Integrate NavBar + Breadcrumbs

- [ ] Remove floating `SiteLogo` and `ThemeToggle` from `App.tsx`
- [ ] Add `NavBar` as persistent element above `Routes`
- [ ] Add `Breadcrumbs` to each view that needs it (or pass via layout wrapper)

#### E. Session Detail — Campaign Context

- [ ] In `SessionDetail.tsx`: if session has `campaign_id`, fetch campaign name for breadcrumbs
- [ ] Breadcrumb links back to campaign detail, not just session list

#### F. Documentation

- [ ] Add ticket entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/frontend/src/components/NavBar.tsx` | Persistent navigation bar |
| `app/frontend/src/components/Breadcrumbs.tsx` | Reusable breadcrumb component |

### Files to Modify

| File | Action |
|------|--------|
| `app/frontend/src/App.tsx` | Update routes, replace floating components with NavBar |
| `app/frontend/src/views/CampaignDetail.tsx` | Add breadcrumbs |
| `app/frontend/src/views/SessionDetail.tsx` | Add campaign-aware breadcrumbs |
| `app/frontend/src/views/NewSessionForm.tsx` | Add breadcrumbs |
| `app/frontend/src/views/NewCampaignForm.tsx` | Add breadcrumbs |
| `app/frontend/src/views/SessionList.tsx` | Add breadcrumbs |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should NOT Modify

- Any backend code
- `app/frontend/src/components/SessionCard.tsx` — unchanged
- `app/frontend/src/components/CampaignCard.tsx` — unchanged

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/frontend/src/App.tsx` | Current routes + floating components |
| `app/frontend/src/views/SessionDetail.tsx` | Existing breadcrumb pattern |
| `app/frontend/src/design/tokens.ts` | Design tokens |

---

## Suggested Implementation Pattern

```typescript
// NavBar.tsx
export default function NavBar() {
  const location = useLocation()
  return (
    <nav style={s.bar}>
      <a href="/campaigns" style={s.logo}>
        <img src="/nerdy-logo.png" alt="Nerdy" style={{ width: 80 }} />
      </a>
      <div style={s.links}>
        <NavLink to="/campaigns" active={location.pathname.startsWith('/campaigns')}>
          Campaigns
        </NavLink>
        <NavLink to="/sessions" active={location.pathname === '/sessions'}>
          All Sessions
        </NavLink>
        <NavLink to="/dashboard" active={location.pathname === '/dashboard'}>
          Dashboard
        </NavLink>
      </div>
      <ThemeToggle />
    </nav>
  )
}
```

```typescript
// Breadcrumbs.tsx
interface Crumb { label: string; path?: string }
export default function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <div style={s.wrap}>
      {items.map((item, i) => (
        <span key={i}>
          {i > 0 && <span style={s.sep}> / </span>}
          {item.path ? <a href={item.path} style={s.link}>{item.label}</a> : <span>{item.label}</span>}
        </span>
      ))}
    </div>
  )
}
```

---

## Edge Cases to Handle

1. Direct navigation to `/sessions/:id` (no campaign context) — breadcrumb shows `Sessions / [Name]`
2. Session belongs to campaign but user navigated via flat `/sessions` list — show campaign breadcrumb if `campaign_id` exists
3. Campaign or session name very long — truncate in breadcrumbs with ellipsis
4. Mobile viewport — nav bar should be usable (stack or hamburger)
5. Theme toggle must still work after moving from floating to nav bar

---

## Definition of Done

- [ ] `/` redirects to `/campaigns`
- [ ] NavBar renders on all pages with active indicators
- [ ] Breadcrumbs shown on CampaignDetail, SessionDetail, NewSessionForm, NewCampaignForm
- [ ] Campaign-aware breadcrumbs in SessionDetail when session has campaign_id
- [ ] Floating logo and theme toggle removed, replaced by NavBar
- [ ] All navigation flows work (campaign → session → back)
- [ ] Design consistent with existing tokens
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| NavBar component | 20 min |
| Breadcrumbs component | 10 min |
| Route updates | 5 min |
| Integrate into views | 15 min |
| Session campaign context | 10 min |
| DEVLOG | 5 min |

---

## After This Ticket: What Comes Next

- **PC-11:** Campaign roll-up stats
- **PC-12:** Campaign archiving + management
