// Ad-Ops-Autopilot — App router
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import SessionList from './views/SessionList'
import NewSessionForm from './views/NewSessionForm'
import SessionDetail from './views/SessionDetail'
import WatchLive from './views/WatchLive'
import SharedSession from './views/SharedSession'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/sessions" replace />} />
        <Route path="/sessions" element={<SessionList />} />
        <Route path="/sessions/new" element={<NewSessionForm />} />
        <Route path="/sessions/:sessionId" element={<SessionDetail />} />
        <Route path="/sessions/:sessionId/live" element={<WatchLive />} />
        <Route path="/shared/:token" element={<SharedSession />} />
      </Routes>
    </BrowserRouter>
  )
}
