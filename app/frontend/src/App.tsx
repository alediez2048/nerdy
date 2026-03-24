// Ad-Ops-Autopilot — App router
// PC-10: Navigation update — campaigns as home, persistent NavBar
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { SignedIn, SignedOut, SignIn } from '@clerk/clerk-react'
import { colors, font } from './design/tokens'
import SessionList from './views/SessionList'
import NewSessionForm from './views/NewSessionForm'
import SessionDetail from './views/SessionDetail'
import WatchLive from './views/WatchLive'
import SharedSession from './views/SharedSession'
import GlobalDashboard from './views/GlobalDashboard'
import CampaignList from './views/CampaignList'
import NewCampaignForm from './views/NewCampaignForm'
import CampaignDetail from './views/CampaignDetail'
import CompetitiveIntelPage from './views/CompetitiveIntelPage'
import CuratedSetPage from './views/CuratedSetPage'
import GlobalAdLibrary from './views/GlobalAdLibrary'
import NavBar from './components/NavBar'

const CLERK_ENABLED = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

function AuthGate({ children }: { children: React.ReactNode }) {
  if (!CLERK_ENABLED) return <>{children}</>

  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        <div style={authStyles.page}>
          <div style={authStyles.card}>
            <img src="/nerdy-logo.png" alt="Nerdy" style={authStyles.logo} />
            <p style={authStyles.tagline}>
              Generate, evaluate, and curate high-performing<br />
              Facebook & Instagram ads — powered by AI.
            </p>
            <div style={authStyles.signInWrap}>
              <SignIn
                routing="hash"
                appearance={{
                  elements: {
                    rootBox: {
                      width: '100%',
                      display: 'flex',
                      justifyContent: 'center',
                    },
                    cardBox: {
                      width: '100%',
                      maxWidth: '420px',
                    },
                    socialButtonsBlockButton: {
                      backgroundColor: '#ffffff',
                      color: '#1f1f1f',
                      border: '1px solid #dadce0',
                    },
                    socialButtonsBlockButtonText: {
                      color: '#1f1f1f',
                      fontWeight: 500,
                    },
                  },
                }}
              />
            </div>
          </div>
        </div>
      </SignedOut>
    </>
  )
}

const authStyles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: `linear-gradient(135deg, ${colors.ink} 0%, #0d1b2a 50%, ${colors.ink} 100%)`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: font.family,
    padding: '20px',
  },
  card: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
    padding: '48px 32px',
    maxWidth: '420px',
    width: '100%',
    boxSizing: 'border-box',
  },
  logo: {
    width: '140px',
    height: 'auto',
    marginBottom: '20px',
  },
  tagline: {
    color: colors.muted,
    fontSize: '15px',
    lineHeight: 1.6,
    margin: '0 0 36px',
  },
  signInWrap: {
    width: '100%',
    display: 'flex',
    justifyContent: 'center',
  },
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthGate>
        <NavBar />
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/sessions" element={<SessionList />} />
          <Route path="/sessions/new" element={<NewSessionForm />} />
          <Route path="/sessions/:sessionId" element={<SessionDetail />} />
          <Route path="/sessions/:sessionId/live" element={<WatchLive />} />
          <Route path="/shared/:token" element={<SharedSession />} />
          <Route path="/dashboard" element={<GlobalDashboard />} />
          <Route path="/campaigns" element={<CampaignList />} />
          <Route path="/campaigns/new" element={<NewCampaignForm />} />
          <Route path="/campaigns/:campaignId" element={<CampaignDetail />} />
          <Route path="/campaigns/:campaignId/sessions/new" element={<NewSessionForm />} />
          <Route path="/ads" element={<GlobalAdLibrary />} />
          <Route path="/competitive" element={<CompetitiveIntelPage />} />
          <Route path="/curated" element={<CuratedSetPage />} />
        </Routes>
      </AuthGate>
    </BrowserRouter>
  )
}
