// PJ-07 — Onboarding wizard view.
//
// Wraps the reusable <Chat /> component with the 5-dot phase progress
// bar and the redirect-on-completion behavior. Sits at /onboarding;
// App.tsx routes here whenever the user's brand_profile isn't yet
// `good_enough`.
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchProfileStatus } from '../api/agent'
import Chat from '../components/Chat'
import PhaseProgress from '../components/PhaseProgress'
import { colors, font } from '../design/tokens'
import useMediaQuery from '../hooks/useMediaQuery'
import type { Phase } from '../types/agent'

export default function Onboarding() {
  const isMobile = useMediaQuery('(max-width: 767px)')
  const navigate = useNavigate()
  const [phase, setPhase] = useState<Phase>('identify')
  // The Chat component reports phase transitions; we poll profile
  // status on each one (cheap GET) and redirect the user out of the
  // wizard the first time `good_enough_now` flips true.
  const redirectedRef = useRef(false)

  useEffect(() => {
    if (redirectedRef.current) return
    if (phase !== 'good_enough' && phase !== 'complete') return
    fetchProfileStatus()
      .then((status) => {
        if (status.good_enough_now && !redirectedRef.current) {
          redirectedRef.current = true
          navigate('/sessions', { replace: true })
        }
      })
      .catch(() => {})
  }, [phase, navigate])

  return (
    <div style={s.pageBg}>
      <div
        style={{
          ...s.pageInner,
          padding: isMobile ? '88px 16px 24px' : s.pageInner.padding,
        }}
      >
        <h1 style={s.title}>Welcome to AdEngine</h1>
        <p style={s.subtitle}>
          Let's set up your brand. The assistant will ask a handful of
          questions — under ten minutes, end-to-end. You can drop a logo
          or style guide directly into the chat at any point.
        </p>

        <PhaseProgress phase={phase} />

        <Chat
          touchpoint="onboarding"
          onPhaseChange={setPhase}
          onCompleted={() => {
            // Agent emitted `finish_touchpoint`. Belt-and-suspenders
            // navigate even though the phase effect above usually
            // beats us to it.
            if (!redirectedRef.current) {
              redirectedRef.current = true
              navigate('/sessions', { replace: true })
            }
          }}
        />
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
    padding: '96px 20px 32px',
  },
  title: {
    color: colors.white,
    fontSize: '28px',
    fontWeight: 700,
    margin: '0 0 8px',
  },
  subtitle: {
    color: colors.muted,
    fontSize: '14px',
    lineHeight: 1.5,
    margin: '0 0 12px',
  },
}
