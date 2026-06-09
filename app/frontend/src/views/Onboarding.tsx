// PJ-07 — Onboarding wizard view.
//
// Wraps the reusable <Chat /> component with the 5-dot phase progress
// bar and the redirect-on-completion behavior. Sits at /onboarding;
// App.tsx routes here whenever the user's brand_profile isn't yet
// `good_enough`.
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Chat from '../components/Chat'
import PhaseProgress from '../components/PhaseProgress'
import { colors, font } from '../design/tokens'
import useMediaQuery from '../hooks/useMediaQuery'
import type { Phase } from '../types/agent'

export default function Onboarding() {
  const isMobile = useMediaQuery('(max-width: 767px)')
  const navigate = useNavigate()
  const [phase, setPhase] = useState<Phase>('identify')

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
            // Brand profile is good_enough — let the user out of the
            // wizard. Sessions become creatable on the next page load.
            navigate('/sessions', { replace: true })
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
