// Ad-Ops-Autopilot — App router
import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import SessionList from './views/SessionList'
import NewSessionForm from './views/NewSessionForm'
import SessionDetail from './views/SessionDetail'
import WatchLive from './views/WatchLive'
import SharedSession from './views/SharedSession'
import GlobalDashboard from './views/GlobalDashboard'

function ThemeToggle() {
  const [light, setLight] = useState(() => localStorage.getItem('theme') === 'light')

  useEffect(() => {
    document.body.classList.toggle('light-mode', light)
    localStorage.setItem('theme', light ? 'light' : 'dark')
  }, [light])

  return (
    <button
      onClick={() => setLight(!light)}
      style={{
        position: 'fixed',
        top: '16px',
        right: '16px',
        zIndex: 9999,
        padding: '8px 16px',
        borderRadius: '100px',
        border: '1px solid rgba(255,255,255,0.2)',
        background: 'rgba(255,255,255,0.1)',
        color: '#fff',
        cursor: 'pointer',
        fontSize: '13px',
        fontFamily: "'Poppins', sans-serif",
        backdropFilter: 'blur(8px)',
      }}
    >
      {light ? '☾ Dark' : '☀ Light'}
    </button>
  )
}

function SiteLogo() {
  return (
    <a
      href="/sessions"
      style={{
        position: 'fixed',
        top: '16px',
        left: '16px',
        zIndex: 9999,
        display: 'block',
      }}
      aria-label="Go to Sessions"
    >
      <img
        src="/nerdy-logo.png"
        alt="Nerdy"
        style={{
          width: '92px',
          height: 'auto',
          display: 'block',
        }}
      />
    </a>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <SiteLogo />
      <ThemeToggle />
      <Routes>
        <Route path="/" element={<Navigate to="/sessions" replace />} />
        <Route path="/sessions" element={<SessionList />} />
        <Route path="/sessions/new" element={<NewSessionForm />} />
        <Route path="/sessions/:sessionId" element={<SessionDetail />} />
        <Route path="/sessions/:sessionId/live" element={<WatchLive />} />
        <Route path="/shared/:token" element={<SharedSession />} />
        <Route path="/dashboard" element={<GlobalDashboard />} />
      </Routes>
    </BrowserRouter>
  )
}
