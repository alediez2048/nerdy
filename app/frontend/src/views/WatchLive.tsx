// PA-08: Watch Live — SSE-powered real-time progress view
import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { colors, font } from '../design/tokens'
import useSessionProgress from '../hooks/useSessionProgress'
import CycleIndicator from '../components/progress/CycleIndicator'
import AdCountBar from '../components/progress/AdCountBar'
import ScoreFeed from '../components/progress/ScoreFeed'
import CostAccumulator from '../components/progress/CostAccumulator'
import QualityTrend from '../components/progress/QualityTrend'
import LatestAdPreview from '../components/progress/LatestAdPreview'

export default function WatchLive() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const { progress, history, connected, error } = useSessionProgress(sessionId!)

  // Auto-redirect on completion
  useEffect(() => {
    if (progress?.type === 'pipeline_complete') {
      const timer = setTimeout(() => navigate(`/sessions/${sessionId}`), 1500)
      return () => clearTimeout(timer)
    }
  }, [progress, sessionId, navigate])

  const adTarget = 50 // Default, could come from session config

  return (
    <div style={s.pageBg}>
      <div style={s.pageInner}>
        {/* Header */}
        <div style={s.header}>
          <div>
            <span onClick={() => navigate('/sessions')} style={s.back}>← Sessions</span>
            <h1 style={s.title}>Watch Live</h1>
          </div>
          <div style={s.status}>
            <span style={{ ...s.dot, background: connected ? colors.mint : error ? colors.red : colors.yellow }} />
            <span style={{ color: colors.muted, fontSize: '12px' }}>
              {connected ? 'Connected' : error ? 'Disconnected' : 'Reconnecting...'}
            </span>
          </div>
        </div>

        {error && <p style={s.error}>{error}</p>}

        {progress?.type === 'pipeline_complete' && (
          <div style={s.completeBar}>Pipeline complete — redirecting to dashboard...</div>
        )}

        {progress?.type === 'pipeline_error' && (
          <div style={s.errorBar}>Pipeline failed: {progress.error || 'Unknown error'}</div>
        )}

        {/* 6 live elements — 2x3 grid */}
        <div style={s.grid}>
          <CycleIndicator progress={progress} />
          <AdCountBar progress={progress} target={adTarget} />
          <ScoreFeed history={history} />
          <CostAccumulator progress={progress} />
          <QualityTrend history={history} />
          <LatestAdPreview history={history} />
        </div>
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  pageBg: {
    minHeight: '100vh',
    width: '100%',
    background: colors.ink,
    fontFamily: font.family,
  },
  pageInner: {
    maxWidth: '900px',
    margin: '0 auto',
    padding: '32px 20px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '24px',
  },
  back: { color: colors.cyan, cursor: 'pointer', fontSize: '13px' },
  title: {
    fontSize: '28px',
    fontWeight: 700,
    margin: '4px 0 0',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  status: { display: 'flex', alignItems: 'center', gap: '6px', marginTop: '8px' },
  dot: { width: '8px', height: '8px', borderRadius: '50%', display: 'inline-block' },
  error: { color: colors.red, fontSize: '14px', marginBottom: '12px' },
  completeBar: {
    background: `${colors.mint}20`,
    color: colors.mint,
    padding: '12px 20px',
    borderRadius: '12px',
    marginBottom: '16px',
    textAlign: 'center',
    fontWeight: 600,
  },
  errorBar: {
    background: `${colors.red}20`,
    color: colors.red,
    padding: '12px 20px',
    borderRadius: '12px',
    marginBottom: '16px',
    textAlign: 'center',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
    gap: '12px',
  },
}
