import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'

// Public pages
import Landing        from './pages/Landing'
import Demo           from './pages/Demo'
import Creator        from './pages/Creator'
import Login          from './pages/Login'
import Register       from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'

// App pages (protected)
import Dashboard     from './pages/Dashboard'
import Upload        from './pages/Upload'
import Meetings      from './pages/Meetings'
import MeetingDetail from './pages/MeetingDetail'
import Summaries     from './pages/Summaries'
import Chat          from './pages/Chat'
import Tasks         from './pages/Tasks'
import Analytics     from './pages/Analytics'
import Settings      from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>

        {/* ── Public routes ── */}
        <Route path="/"              element={<Landing />}        />
        <Route path="/demo"          element={<Demo />}           />
        <Route path="/creator"       element={<Creator />}        />
        <Route path="/login"         element={<Login />}          />
        <Route path="/register"      element={<Register />}       />
        <Route path="/forgot-password" element={<ForgotPassword />} />

        {/* ── Protected app routes ── */}
        <Route path="/app" element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }>
          <Route index               element={<Dashboard />}     />
          <Route path="upload"       element={<Upload />}        />
          <Route path="meetings"     element={<Meetings />}      />
          <Route path="meetings/:id" element={<MeetingDetail />} />
          <Route path="summaries"    element={<Summaries />}     />
          <Route path="chat"         element={<Chat />}          />
          <Route path="tasks"        element={<Tasks />}         />
          <Route path="analytics"    element={<Analytics />}     />
          <Route path="settings"     element={<Settings />}      />
        </Route>

        {/* ── Catch all ── */}
        <Route path="*" element={<Navigate to="/" replace />} />

      </Routes>
    </BrowserRouter>
  )
}