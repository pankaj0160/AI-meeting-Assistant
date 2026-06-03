import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Meetings from './pages/Meetings'
import MeetingDetail from './pages/MeetingDetail'
import Chat from './pages/Chat'
import Tasks from './pages/Tasks'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'
import Summaries from './pages/Summaries'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/"              element={<Dashboard />}     />
          <Route path="/upload"        element={<Upload />}        />
          <Route path="/meetings"      element={<Meetings />}      />
          <Route path="/meetings/:id"  element={<MeetingDetail />} />
          <Route path="/summaries"     element={<Summaries />}     />
          <Route path="/chat"          element={<Chat />}          />
          <Route path="/tasks"         element={<Tasks />}         />
          <Route path="/analytics"     element={<Analytics />}     />
          <Route path="/settings"      element={<Settings />}      />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}