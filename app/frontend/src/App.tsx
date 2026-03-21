// Ad-Ops-Autopilot — App router
// PC-10: Navigation update — campaigns as home, persistent NavBar
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
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
import NavBar from './components/NavBar'

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<Navigate to="/campaigns" replace />} />
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
        <Route path="/competitive" element={<CompetitiveIntelPage />} />
      </Routes>
    </BrowserRouter>
  )
}
