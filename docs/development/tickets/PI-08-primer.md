# PI-08 Primer

**Source plan:** [`PI-PLAN.md`](PI-PLAN.md) — sliced from the ticket section below.
**Phase plan:** [`PI-00-phase-plan.md`](PI-00-phase-plan.md)

**Status:** ⏳ Not started

---

# Ticket PI-08: `VariantsPanel` UI — Evidence panel + legacy badge

**Goal:** Frontend handles both v1 and v2 response shapes. v2 variant cards reveal an Evidence panel with per-dimension scores + rationales; legacy sessions show a "Legacy scoring" badge. Video sessions get unblocked in the Ad Library.

**Files:**
- Modify: `app/frontend/src/api/dashboard.ts` — TypeScript types
- Modify: `app/frontend/src/components/VariantsPanel.tsx` — Evidence panel + legacy branch
- Modify: `app/frontend/src/tabs/AdLibrary.tsx` — remove the video-session hide guard
- Test: smoke check via `npm run build` and manual browser

- [ ] **Step 1: Update `app/frontend/src/api/dashboard.ts`** — extend types to allow both v1 and v2 shapes:

```typescript
export interface DimensionScore {
  score: number
  weight: number
  rationale: string
}
export interface GateEvaluation {
  triggered: boolean
  rationale: string
}
export interface AdVariantV2 {
  variant_type: string
  media_type: 'image' | 'video'
  image_path: string | null
  image_url: string | null
  model_used: string
  predicted_cost_usd: number
  composite_score: number
  raw_score: number
  penalty_multiplier: number
  dimensions: Record<string, DimensionScore>
  penalty_gates: Record<string, GateEvaluation>
  is_winner: boolean
  rejection_reason?: {
    composite_delta: number
    worst_dimension: string
    worst_dimension_delta: number
    worst_dimension_rationale: string
  }
}
export interface AdVariantsV2Response {
  session_id: string
  ad_id: string
  schema_version: 'v2'
  selection_criteria: {
    formula: string
    winner_variant_type: string
    winner_composite_score: number
  }
  winner_reason: {
    composite_score: number
    distinguishing_dimensions: Array<{ dimension: string; delta_vs_mean?: number; absolute_score?: number; note?: string }>
  } | null
  variants: AdVariantV2[]
}
export type AnyVariantsResponse = AdVariantsResponse | AdVariantsV2Response
```

Update the `fetchAdVariants` return type:

```typescript
export const fetchAdVariants = (sessionId: string, adId: string) =>
  get<AnyVariantsResponse>(`${BASE}/${sessionId}/ads/${adId}/variants`)
```

- [ ] **Step 2: Update `VariantsPanel.tsx` — branch on `schema_version`**

Top of the component, after fetching `data`:

```typescript
const isV2 = (data as AdVariantsV2Response).schema_version === 'v2'
if (!isV2) {
  // Render the existing legacy view with a badge.
  return (
    <div style={styles.container}>
      <div style={{ ...styles.header, color: colors.muted, fontStyle: 'italic' }}>
        Legacy scoring (pre-2026-05-15) — per-dimension breakdown not available.
      </div>
      {/* existing v1 grid as today */}
    </div>
  )
}
```

For v2, render the new card shape with the Evidence expander:

```tsx
function EvidencePanel({ variant }: { variant: AdVariantV2 }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{ marginTop: '8px' }}>
      <button onClick={() => setOpen(!open)} style={styles.expander}>
        {open ? '▾' : '▸'} Evidence
      </button>
      {open && (
        <div style={styles.evidence}>
          <table style={{ width: '100%', fontSize: font.xs }}>
            <thead><tr><th>Dimension</th><th>Score</th><th>Weight</th><th>Rationale</th></tr></thead>
            <tbody>
              {Object.entries(variant.dimensions).map(([name, d]) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td>{d.score}/10</td>
                  <td>{(d.weight * 100).toFixed(0)}%</td>
                  <td style={{ fontStyle: 'italic' }}>{d.rationale}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {Object.entries(variant.penalty_gates).filter(([, g]) => g.triggered).length > 0 && (
            <div style={{ marginTop: '8px', color: colors.danger }}>
              <strong>Triggered gates:</strong>
              <ul>
                {Object.entries(variant.penalty_gates)
                  .filter(([, g]) => g.triggered)
                  .map(([name, g]) => (
                    <li key={name}>{name} — {g.rationale}</li>
                  ))}
              </ul>
            </div>
          )}
          <div style={{ marginTop: '8px', color: colors.muted }}>
            raw {variant.raw_score.toFixed(2)} × penalty {variant.penalty_multiplier.toFixed(2)}
            = composite {variant.composite_score.toFixed(1)}
          </div>
        </div>
      )}
    </div>
  )
}
```

Replace the existing `describeReason` block with v2 versions:

```typescript
function describeWinnerReason(reason: AdVariantsV2Response['winner_reason']): string {
  if (!reason || !reason.distinguishing_dimensions.length) return ''
  const dims = reason.distinguishing_dimensions
    .map(d => `${d.dimension} ${d.delta_vs_mean != null ? `+${d.delta_vs_mean}` : `(score ${d.absolute_score})`}`)
    .join(', ')
  return `Why this won: top vs mean of other variants — ${dims}`
}

function describeRejection(v: AdVariantV2): string {
  if (!v.rejection_reason) return ''
  const r = v.rejection_reason
  return `Lost on ${r.worst_dimension}: ${r.worst_dimension_delta} score delta (composite ${r.composite_delta}). ${r.worst_dimension_rationale}`
}
```

- [ ] **Step 3: Unblock video sessions in `AdLibrary.tsx`**

Find the existing guard that hides VariantsPanel for video sessions (commit `2c527e8`). Remove it — the unified `media_type` field lets the same component render video variants. (Video thumbnails will use existing image_url for the first-frame poster when present.)

- [ ] **Step 4: Smoke test**

```
cd app/frontend && npm run build 2>&1 | tail -10
```

Expected: build succeeds, no TypeScript errors.

Manual browser test:
- Start the dev server: `cd app/frontend && npm run dev`
- Sign in, open a session whose ledger has v2 events, expand a variant card → Evidence panel shows 8 dimensions with rationales
- Open a legacy session → "Legacy scoring (pre-2026-05-15)" badge visible

- [ ] **Step 5: Commit**

```
git add app/frontend/src/api/dashboard.ts app/frontend/src/components/VariantsPanel.tsx app/frontend/src/tabs/AdLibrary.tsx
git commit -m "feat(PI-08): VariantsPanel Evidence panel + legacy badge + video unblock"
```

---
