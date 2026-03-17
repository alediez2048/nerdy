// PA-11: Shared session view — read-only, no auth required
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { colors, font } from '../design/tokens'
import { StatusBadge } from '../components/Badge'

interface SharedData {
  session_id: string
  name: string | null
  status: string
  config: Record<string, unknown>
  results_summary: Record<string, unknown> | null
  created_at: string | null
  read_only: boolean
}

export default function SharedSession() {
  const { token } = useParams<{ token: string }>()
  const [data, setData] = useState<SharedData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`/api/shared/${token}`)
      .then((resp) => {
        if (!resp.ok) throw new Error(resp.status === 404 ? 'This share link is invalid, expired, or revoked.' : `HTTP ${resp.status}`)
        return resp.json()
      })
      .then(setData)
      .catch((e) => setError(e.message))
  }, [token])

  if (error) {
    return (
      <div style={s.pageBg}>
        <div style={s.pageInner}>
          <div style={s.errorCard}>
            <h2 style={s.errorTitle}>Share Link Unavailable</h2>
            <p style={s.errorText}>{error}</p>
          </div>
        </div>
      </div>
    )
  }

  if (!data) return <div style={s.pageBg}><div style={s.pageInner}><p style={{ color: colors.muted }}>Loading...</p></div></div>

  const results = data.results_summary || {}
  const config = data.config || {}

  return (
    <div style={s.pageBg}>
      <div style={s.pageInner}>
        <div style={s.banner}>Shared View — Read Only</div>

        <h1 style={s.title}>{data.name || data.session_id}</h1>
        <div style={s.meta}>
          <StatusBadge status={data.status} />
          <span style={{ color: colors.muted, fontSize: '13px' }}>
            {(config.audience as string) || ''} · {(config.campaign_goal as string) || ''}
          </span>
          {data.created_at && (
            <span style={{ color: colors.muted, fontSize: '12px' }}>
              {new Date(data.created_at).toLocaleDateString()}
            </span>
          )}
        </div>

        {/* Summary metrics */}
        {Object.keys(results).length > 0 && (
          <div style={s.grid}>
            {results.ads_generated != null && <Metric label="Generated" value={String(results.ads_generated)} />}
            {results.ads_published != null && <Metric label="Published" value={String(results.ads_published)} />}
            {results.avg_score != null && <Metric label="Avg Score" value={(results.avg_score as number).toFixed(1)} />}
            {results.cost_so_far != null && <Metric label="Cost" value={`$${(results.cost_so_far as number).toFixed(2)}`} />}
          </div>
        )}

        <p style={s.hint}>
          Full dashboard available to session owner. This shared view shows summary metrics only.
        </p>
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ textAlign: 'center', padding: '16px', background: colors.surface, borderRadius: '16px' }}>
      <div style={{ fontSize: '24px', fontWeight: 700, color: colors.white, fontFamily: font.family }}>{value}</div>
      <div style={{ fontSize: '12px', color: colors.muted, fontFamily: font.family }}>{label}</div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  pageBg: { minHeight: '100vh', width: '100%', background: colors.ink, fontFamily: font.family },
  pageInner: { maxWidth: '800px', margin: '0 auto', padding: '32px 20px' },
  banner: {
    background: `${colors.yellow}20`, color: colors.yellow, padding: '10px 20px',
    borderRadius: '12px', textAlign: 'center', fontWeight: 600, fontSize: '13px', marginBottom: '24px',
  },
  title: { fontSize: '28px', fontWeight: 700, color: colors.white, margin: '0 0 12px' },
  meta: { display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '12px', marginBottom: '24px' },
  hint: { color: colors.muted, fontSize: '13px', textAlign: 'center' },
  errorCard: { textAlign: 'center', padding: '60px 20px', background: colors.surface, borderRadius: '24px' },
  errorTitle: { fontSize: '20px', fontWeight: 600, color: colors.white, margin: '0 0 8px' },
  errorText: { fontSize: '14px', color: colors.muted },
}
