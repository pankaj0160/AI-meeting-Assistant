// client/src/App.jsx

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import ErrorBoundary from './components/ErrorBoundary'

// Public pages
import Landing        from './pages/Landing'
import Demo           from './pages/Demo'
import Creator        from './pages/Creator'
import Login          from './pages/Login'
import Register       from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import Support        from './pages/Support'

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

// FIX: PageBoundary wraps each individual page route.
//
// Why per-page boundaries instead of just one global one?
//
//   Without per-page:  Dashboard crashes → entire Layout (sidebar + navbar)
//                      disappears → user is completely stuck
//
//   With per-page:     Dashboard crashes → only the content area shows the
//                      error card → sidebar still works → user navigates
//                      to Tasks or Settings → app keeps running normally
//
// This is much better UX — one broken page doesn't kill the whole app.
//
// Each boundary gets a meaningful fallbackTitle so the error card
// tells the user WHICH section broke, not just "something went wrong".

function PageBoundary({ title, children }) {
  return (
    <ErrorBoundary
      fallbackTitle={`${title} ran into a problem`}
      fallbackMessage={`The ${title} page encountered an unexpected error. Try reloading or go back to the dashboard.`}
      showHome={true}
    >
      {children}
    </ErrorBoundary>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>

        {/* ── Public routes ── */}
        {/* Public pages don't need per-page boundaries — the app-level one
            in main.jsx covers them. Landing, Login etc. are simple and
            rarely crash. Adding boundaries everywhere adds noise. */}
        <Route path="/"               element={<Landing />}        />
        <Route path="/demo"           element={<Demo />}           />
        <Route path="/creator"        element={<Creator />}        />
        <Route path="/login"          element={<Login />}          />
        <Route path="/register"       element={<Register />}       />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/support"        element={<Support />}        />

        {/* ── Protected app routes ── */}
        {/* FIX: every page is now wrapped in its own ErrorBoundary via PageBoundary.
            If MeetingDetail crashes (e.g. bad API data), only that page shows
            the error — the sidebar, nav, and all other pages keep working. */}
        <Route path="/app" element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }>
          <Route index               element={
            <PageBoundary title="Dashboard">
              <Dashboard />
            </PageBoundary>
          } />

          <Route path="upload"       element={
            <PageBoundary title="Upload">
              <Upload />
            </PageBoundary>
          } />

          <Route path="meetings"     element={
            <PageBoundary title="Meetings">
              <Meetings />
            </PageBoundary>
          } />

          <Route path="meetings/:id" element={
            <PageBoundary title="Meeting Detail">
              <MeetingDetail />
            </PageBoundary>
          } />

          <Route path="summaries"    element={
            <PageBoundary title="Summaries">
              <Summaries />
            </PageBoundary>
          } />

          <Route path="chat"         element={
            <PageBoundary title="Chat">
              <Chat />
            </PageBoundary>
          } />

          <Route path="tasks"        element={
            <PageBoundary title="Tasks">
              <Tasks />
            </PageBoundary>
          } />

          <Route path="analytics"    element={
            <PageBoundary title="Analytics">
              <Analytics />
            </PageBoundary>
          } />

          <Route path="settings"     element={
            <PageBoundary title="Settings">
              <Settings />
            </PageBoundary>
          } />
        </Route>

        {/* ── Catch all ── */}
        <Route path="*" element={<Navigate to="/" replace />} />

      </Routes>
    </BrowserRouter>
  )
}