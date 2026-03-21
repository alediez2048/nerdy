// Expanded brief from ledger BriefExpanded events (QA / transparency)
// Falls back to session config when the ledger has no BriefExpanded rows yet.
import { useEffect, useState } from 'react'
import { colors, radii, font } from '../design/tokens'
import { fetchBriefExpansions } from '../api/sessions'
import { PERSONA_LABELS, type Persona } from '../types/session'

interface BriefEvent {
  timestamp?: string
  brief_id?: string
  inputs?: Record<string, unknown>
  outputs?: Record<string, unknown>
}

/** Readable session brief when ledger has no BriefExpanded events */
function SessionBriefFromConfig({ config }: { config: Record<string, unknown> }) {
  const str = (k: string) => {
    const v = config[k]
    if (v === undefined || v === null) return null
    const s = String(v).trim()
    return s === '' ? null : s
  }
  const personaKey = str('persona')
  const personaLabel =
    personaKey && personaKey in PERSONA_LABELS
      ? PERSONA_LABELS[personaKey as Persona]
      : personaKey

  const rows: { label: string; value: string }[] = []
  const add = (label: string, key: string) => {
    const v = str(key)
    if (v) rows.push({ label, value: v })
  }

  const sessionType = str('session_type') || 'image'
  const isVideo = sessionType === 'video'

  add('Session type', 'session_type')
  add('Audience', 'audience')
  add('Campaign goal', 'campaign_goal')
  if (personaLabel) rows.push({ label: 'Persona', value: personaLabel })
  add('Key message', 'key_message')
  add('Creative brief', 'creative_brief')

  // Image-only fields
  if (!isVideo) {
    add('Ad count', 'ad_count')
    add('Cycle count', 'cycle_count')
    add('Quality threshold', 'quality_threshold')
    add('Aspect ratio (image)', 'aspect_ratio')
    add('Copy on image', 'copy_on_image')
  }

  // Video-only fields
  if (isVideo) {
    add('Video provider', 'video_provider')
    add('Fal video model', 'video_fal_model')
    add('Video count', 'video_count')
    add('Video duration (s)', 'video_duration')
    add('Video aspect ratio', 'video_aspect_ratio')
    add('Video scene', 'video_scene')
    add('Visual style', 'video_visual_style')
    add('Camera movement', 'video_camera_movement')
    add('Subject / action', 'video_subject_action')
    add('Setting', 'video_setting')
    add('Lighting / mood', 'video_lighting_mood')
    add('Audio detail', 'video_audio_detail')
    add('Color palette', 'video_color_palette')
    add('Negative prompt', 'video_negative_prompt')
  }

  if (rows.length === 0) {
    return (
      <p style={{ color: colors.muted, fontFamily: font.family }}>
        No brief fields found in session config.
      </p>
    )
  }

  return (
    <div style={s.card}>
      <div style={s.cardHead}>
        <span style={s.cardTitle}>Session brief (saved config)</span>
      </div>
      <ul style={{ ...s.ul, listStyle: 'none', paddingLeft: 0 }}>
        {rows.map(({ label, value }) => (
          <li key={label} style={{ marginBottom: '10px' }}>
            <strong style={{ color: colors.yellow }}>{label}:</strong>{' '}
            <span style={{ color: colors.white }}>{value}</span>
          </li>
        ))}
      </ul>
      <details style={s.details}>
        <summary style={s.summary}>Raw config JSON</summary>
        <pre style={s.pre}>{JSON.stringify(config, null, 2)}</pre>
      </details>
    </div>
  )
}

export default function ExpandedBriefPanel({
  sessionId,
  sessionConfig,
}: {
  sessionId: string
  /** Session row `config` — shown when ledger has no BriefExpanded events */
  sessionConfig?: Record<string, unknown>
}) {
  const [events, setEvents] = useState<BriefEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setErr(null)
    fetchBriefExpansions(sessionId)
      .then((res) => setEvents(res.events as BriefEvent[]))
      .catch((e) => setErr(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [sessionId])

  if (loading) {
    return <p style={{ color: colors.muted, fontFamily: font.family }}>Loading expanded briefs…</p>
  }
  if (err) {
    return <p style={{ color: colors.red, fontFamily: font.family }}>{err}</p>
  }
  if (events.length === 0) {
    return (
      <div style={s.wrap}>
        <p style={{ ...s.lede, fontFamily: font.family, marginBottom: '16px' }}>
          <strong style={{ color: colors.white }}>Expanded brief</strong> (LLM grounding + angles) is stored in the
          ledger as <code style={s.code}>BriefExpanded</code> after <code style={s.code}>expand_brief()</code> runs.
          This session doesn&apos;t have those rows yet — below is your <strong style={{ color: colors.white }}>session
          brief</strong> from saved config.
        </p>
        {sessionConfig && <SessionBriefFromConfig config={sessionConfig} />}
        <p style={{ color: colors.muted, fontFamily: font.family, lineHeight: 1.6, maxWidth: '640px', marginTop: '20px' }}>
          To capture the full expanded brief in the ledger, re-run the pipeline on this session (or start a new run)
          with current code. You can also inspect{' '}
          <code style={s.code}>data/sessions/&lt;id&gt;/ledger.jsonl</code> for raw events.
        </p>
      </div>
    )
  }

  return (
    <div style={s.wrap}>
      <p style={{ ...s.lede, fontFamily: font.family }}>
        Each card is one brief expansion from the decision ledger (inputs + structured outputs). Use this to debug
        copy and video prompts against the grounded brief.
      </p>
      {events.map((ev, idx) => (
        <BriefEventCard key={`${ev.brief_id ?? idx}-${ev.timestamp ?? idx}`} event={ev} index={idx + 1} />
      ))}
    </div>
  )
}

function BriefEventCard({ event, index }: { event: BriefEvent; index: number }) {
  const inputs = event.inputs ?? {}
  const outputs = event.outputs ?? {}
  const expanded = outputs.expanded_brief as Record<string, unknown> | undefined
  const briefIn = (inputs.brief as Record<string, unknown>) || {}
  const persona = (inputs.persona as string) || (outputs.persona as string) || '—'

  return (
    <div style={s.card}>
      <div style={s.cardHead}>
        <span style={s.cardTitle}>Brief expansion #{index}</span>
        {event.brief_id && (
          <span style={s.badge}>{String(event.brief_id)}</span>
        )}
        {event.timestamp && (
          <span style={s.ts}>{new Date(event.timestamp).toLocaleString()}</span>
        )}
      </div>
      <p style={s.meta}>
        <strong>Persona:</strong> {persona}
      </p>

      {(briefIn.audience || briefIn.campaign_goal || briefIn.key_message) && (
        <div style={s.block}>
          <h4 style={s.h4}>Session / brief inputs</h4>
          <ul style={s.ul}>
            {briefIn.audience != null && <li><strong>Audience:</strong> {String(briefIn.audience)}</li>}
            {briefIn.campaign_goal != null && <li><strong>Goal:</strong> {String(briefIn.campaign_goal)}</li>}
            {briefIn.key_message != null && String(briefIn.key_message).trim() !== '' && (
              <li><strong>Key message:</strong> {String(briefIn.key_message)}</li>
            )}
            {briefIn.product != null && <li><strong>Product:</strong> {String(briefIn.product)}</li>}
          </ul>
        </div>
      )}

      {expanded ? (
        <ExpandedBriefReadable data={expanded} />
      ) : (
        <LegacyOutputs outputs={outputs} />
      )}

      <details style={s.details}>
        <summary style={s.summary}>Raw JSON (full event)</summary>
        <pre style={s.pre}>{JSON.stringify(event, null, 2)}</pre>
      </details>
    </div>
  )
}

function LegacyOutputs({ outputs }: { outputs: Record<string, unknown> }) {
  const angles = outputs.emotional_angles as string[] | undefined
  const vps = outputs.value_propositions as string[] | undefined
  const diffs = outputs.key_differentiators as string[] | undefined
  if (!angles?.length && !vps?.length && !diffs?.length) {
    return (
      <p style={{ color: colors.muted, fontSize: '13px' }}>
        No structured <code style={s.code}>expanded_brief</code> on this event (older pipeline). See raw JSON below.
      </p>
    )
  }
  return (
    <div style={s.block}>
      <h4 style={s.h4}>Partial outputs (legacy ledger)</h4>
      {angles && angles.length > 0 && (
        <>
          <p style={s.h5}>Emotional angles</p>
          <ul style={s.ul}>{angles.map((a) => <li key={a}>{a}</li>)}</ul>
        </>
      )}
      {vps && vps.length > 0 && (
        <>
          <p style={s.h5}>Value propositions</p>
          <ul style={s.ul}>{vps.map((a) => <li key={a}>{a}</li>)}</ul>
        </>
      )}
      {diffs && diffs.length > 0 && (
        <>
          <p style={s.h5}>Key differentiators</p>
          <ul style={s.ul}>{diffs.map((a) => <li key={a}>{a}</li>)}</ul>
        </>
      )}
    </div>
  )
}

function ExpandedBriefReadable({ data }: { data: Record<string, unknown> }) {
  const ctx = data.competitive_context as string | undefined
  const angles = data.emotional_angles as string[] | undefined
  const vps = data.value_propositions as string[] | undefined
  const diffs = data.key_differentiators as string[] | undefined
  const constraints = data.constraints as string[] | undefined
  const brandFacts = data.brand_facts as unknown

  return (
    <>
      {ctx && (
        <div style={s.block}>
          <h4 style={s.h4}>Competitive context</h4>
          <p style={s.para}>{ctx}</p>
        </div>
      )}
      {angles && angles.length > 0 && (
        <div style={s.block}>
          <h4 style={s.h4}>Emotional angles</h4>
          <ul style={s.ul}>{angles.map((a) => <li key={a}>{a}</li>)}</ul>
        </div>
      )}
      {vps && vps.length > 0 && (
        <div style={s.block}>
          <h4 style={s.h4}>Value propositions</h4>
          <ul style={s.ul}>{vps.map((a) => <li key={a}>{a}</li>)}</ul>
        </div>
      )}
      {diffs && diffs.length > 0 && (
        <div style={s.block}>
          <h4 style={s.h4}>Key differentiators</h4>
          <ul style={s.ul}>{diffs.map((a) => <li key={a}>{a}</li>)}</ul>
        </div>
      )}
      {constraints && constraints.length > 0 && (
        <div style={s.block}>
          <h4 style={s.h4}>Constraints</h4>
          <ul style={s.ul}>{constraints.map((a) => <li key={a}>{a}</li>)}</ul>
        </div>
      )}
      {brandFacts != null && (
        <div style={s.block}>
          <h4 style={s.h4}>Brand facts (from KB)</h4>
          <pre style={s.preSm}>{JSON.stringify(brandFacts, null, 2)}</pre>
        </div>
      )}
      <details style={s.details}>
        <summary style={s.summary}>Full expanded_brief object</summary>
        <pre style={s.pre}>{JSON.stringify(data, null, 2)}</pre>
      </details>
    </>
  )
}

const s: Record<string, React.CSSProperties> = {
  wrap: { marginBottom: '24px' },
  lede: { color: colors.muted, fontSize: '14px', marginBottom: '20px', lineHeight: 1.5, maxWidth: '720px' },
  code: { fontSize: '12px', color: colors.cyan },
  card: {
    background: colors.surface,
    borderRadius: radii.card,
    padding: '20px',
    marginBottom: '16px',
    border: `1px solid ${colors.muted}25`,
  },
  cardHead: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px', marginBottom: '12px' },
  cardTitle: { fontSize: '16px', fontWeight: 600, color: colors.white, fontFamily: font.family },
  badge: {
    fontSize: '11px',
    padding: '2px 8px',
    borderRadius: '4px',
    background: `${colors.cyan}22`,
    color: colors.cyan,
    fontFamily: font.family,
  },
  ts: { fontSize: '12px', color: colors.muted, fontFamily: font.family },
  meta: { fontSize: '13px', color: colors.muted, marginBottom: '14px', fontFamily: font.family },
  block: { marginBottom: '16px' },
  h4: { fontSize: '14px', fontWeight: 600, color: colors.yellow, margin: '0 0 8px', fontFamily: font.family },
  h5: { fontSize: '12px', fontWeight: 600, color: colors.white, margin: '8px 0 4px', fontFamily: font.family },
  ul: { margin: '0', paddingLeft: '20px', color: colors.white, fontSize: '13px', lineHeight: 1.55, fontFamily: font.family },
  para: { fontSize: '13px', lineHeight: 1.6, color: colors.white, margin: 0, fontFamily: font.family },
  pre: {
    fontSize: '11px',
    lineHeight: 1.45,
    overflow: 'auto',
    maxHeight: '420px',
    padding: '12px',
    background: colors.ink,
    borderRadius: radii.input,
    border: `1px solid ${colors.muted}20`,
    color: colors.muted,
    fontFamily: 'ui-monospace, monospace',
  },
  preSm: {
    fontSize: '11px',
    lineHeight: 1.45,
    overflow: 'auto',
    maxHeight: '240px',
    padding: '10px',
    background: colors.ink,
    borderRadius: radii.input,
    color: colors.muted,
    fontFamily: 'ui-monospace, monospace',
  },
  details: { marginTop: '12px' },
  summary: { cursor: 'pointer', color: colors.cyan, fontSize: '13px', fontFamily: font.family },
}
