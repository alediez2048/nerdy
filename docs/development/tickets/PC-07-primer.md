# PC-07 Primer: NewCampaignForm Frontend

**For:** New Cursor Agent session
**Project:** Ad-Ops-Autopilot — Autonomous Content Generation System for FB/IG
**Date:** March 2026
**Previous work:** PC-04 (Campaign CRUD API), PC-06 (CampaignList + CampaignCard). See `docs/DEVLOG.md`.

---

## What Is This Ticket?

PC-07 builds the campaign creation form. Users fill in a campaign name, optional description, default audience/goal/persona, and optionally configure default session settings. On submit, the form calls `POST /api/campaigns` and navigates to the new campaign's detail page.

### Why It Matters

- Users need a UI to create campaigns — the API exists (PC-04) but has no frontend
- Default config set here pre-fills session creation within the campaign (PC-09)
- The form should be simple for quick campaign creation but support optional defaults for power users
- Follows the progressive disclosure pattern from `NewSessionForm.tsx`

---

## What Was Already Done

- PC-04: `POST /campaigns` API accepts name, description, audience, campaign_goal, default_config
- PC-06: `app/frontend/src/api/campaigns.ts` — `createCampaign()` client function
- PA-05: `NewSessionForm.tsx` — progressive disclosure form pattern (reference)

---

## What This Ticket Must Accomplish

### Goal

Create a campaign creation form at `/campaigns/new` with required name field, optional metadata, and optional default session config.

### Deliverables Checklist

#### A. Form View (`app/frontend/src/views/NewCampaignForm.tsx` — create)

- [ ] Required field: Campaign name (text input)
- [ ] Optional fields (always visible):
  - Description (textarea)
  - Default audience (parents/students toggle)
  - Default campaign goal (awareness/conversion toggle)
  - Default persona (dropdown, same options as session form)
- [ ] Collapsible "Advanced Defaults" section (progressive disclosure):
  - Default session type (image/video toggle)
  - Default ad count (number input)
  - Default quality threshold (number input)
  - Default model tier (standard/premium toggle)
- [ ] Submit button: "Create Campaign"
- [ ] Loading state during API call
- [ ] Error display on failure
- [ ] On success: navigate to `/campaigns/{campaign_id}`
- [ ] Back link: "← Back to Campaigns"

#### B. Route Registration (`app/frontend/src/App.tsx` — modify)

- [ ] Add route: `/campaigns/new` → `NewCampaignForm`
- [ ] Place BEFORE `/campaigns/:id` to avoid route conflicts

#### C. Documentation

- [ ] Add ticket entry in `docs/DEVLOG.md`

---

## Branch & Merge Workflow

Work on `develop` branch per project convention.

---

## Important Context

### Files to Create

| File | Why |
|------|-----|
| `app/frontend/src/views/NewCampaignForm.tsx` | Campaign creation form |

### Files to Modify

| File | Action |
|------|--------|
| `app/frontend/src/App.tsx` | Add `/campaigns/new` route |
| `docs/DEVLOG.md` | Add ticket entry |

### Files You Should NOT Modify

- `app/frontend/src/views/NewSessionForm.tsx` — session form unchanged
- Any backend code

### Files You Should READ for Context

| File | Why |
|------|-----|
| `app/frontend/src/views/NewSessionForm.tsx` | Form pattern and progressive disclosure |
| `app/frontend/src/api/campaigns.ts` | API client to use |
| `app/frontend/src/types/campaign.ts` | TypeScript types |
| `app/frontend/src/design/tokens.ts` | Design tokens |

---

## Suggested Implementation Pattern

```typescript
export default function NewCampaignForm() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [audience, setAudience] = useState<'parents' | 'students'>('parents')
  const [goal, setGoal] = useState<'awareness' | 'conversion'>('conversion')
  const [persona, setPersona] = useState('auto')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    if (!name.trim()) { setError('Campaign name is required'); return }
    setLoading(true)
    try {
      const result = await createCampaign({
        name: name.trim(),
        description: description.trim() || undefined,
        audience,
        campaign_goal: goal,
        default_config: { persona, /* ...advanced defaults */ },
      })
      navigate(`/campaigns/${result.campaign_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create campaign')
    } finally {
      setLoading(false)
    }
  }
}
```

---

## Edge Cases to Handle

1. Empty campaign name — show inline error, don't submit
2. Very long name — input maxLength=256 (matches DB column)
3. Network error during creation — show error, don't navigate
4. Double-click submit — disable button during loading
5. Browser back during loading — no side effects if component unmounts

---

## Definition of Done

- [ ] Form renders at `/campaigns/new`
- [ ] Name field required, other fields optional
- [ ] Default audience/goal toggles work
- [ ] Advanced defaults section collapsible
- [ ] Submit creates campaign via API
- [ ] Navigates to campaign detail on success
- [ ] Error handling for empty name and API failures
- [ ] Design consistent with NewSessionForm
- [ ] Lint clean
- [ ] DEVLOG updated

---

## Estimated Time

| Task | Estimate |
|------|----------|
| Form component | 25 min |
| Route wiring | 5 min |
| Styling | 10 min |
| DEVLOG | 5 min |

---

## After This Ticket: What Comes Next

- **PC-08:** CampaignDetail view — show campaign info + its sessions
- **PC-09:** Pre-fill session form from campaign defaults
