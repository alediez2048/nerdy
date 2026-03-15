// Ad-Ops-Autopilot — App router
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import NewSessionForm from './views/NewSessionForm'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/sessions" replace />} />
        <Route path="/sessions" element={<PlaceholderList />} />
        <Route path="/sessions/new" element={<NewSessionForm />} />
        <Route path="/sessions/:sessionId" element={<PlaceholderDetail />} />
        <Route path="/sessions/:sessionId/live" element={<PlaceholderLive />} />
      </Routes>
    </BrowserRouter>
  )
}

// Placeholders for PA-06, PA-08, PA-09
function PlaceholderList() {
  return (
    <div style={{ color: '#fff', padding: 40, fontFamily: "'Poppins', sans-serif", background: '#202344', minHeight: '100vh' }}>
      <h1>Sessions</h1>
      <p>Session list coming in PA-06.</p>
      <a href="/sessions/new" style={{ color: '#17e2ea' }}>+ New Session</a>
    </div>
  )
}

function PlaceholderDetail() {
  return (
    <div style={{ color: '#fff', padding: 40, fontFamily: "'Poppins', sans-serif", background: '#202344', minHeight: '100vh' }}>
      <h1>Session Detail</h1>
      <p>Dashboard integration coming in PA-09.</p>
    </div>
  )
}

function PlaceholderLive() {
  return (
    <div style={{ color: '#fff', padding: 40, fontFamily: "'Poppins', sans-serif", background: '#202344', minHeight: '100vh' }}>
      <h1>Watch Live</h1>
      <p>Live progress view coming in PA-08.</p>
    </div>
  )
}
