import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '@/auth/AuthContext'
import { Layout } from '@/components/Layout'
import { RequireAuth } from '@/components/RequireAuth'
import { HomePage } from '@/pages/HomePage'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { AuthCallbackPage } from '@/pages/AuthCallbackPage'
import { SearchPage } from '@/pages/SearchPage'
import { ResultsPage } from '@/pages/ResultsPage'
import { DetailPage } from '@/pages/DetailPage'
import { InterestPage } from '@/pages/InterestPage'
import { ArchivedPage } from '@/pages/ArchivedPage'
import { CalendarPage } from '@/pages/CalendarPage'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="login" element={<LoginPage />} />
            <Route path="register" element={<RegisterPage />} />
            <Route path="auth/callback" element={<AuthCallbackPage />} />
            <Route
              path="search"
              element={
                <RequireAuth>
                  <SearchPage />
                </RequireAuth>
              }
            />
            <Route
              path="results"
              element={
                <RequireAuth>
                  <ResultsPage />
                </RequireAuth>
              }
            />
            <Route
              path="properties/:propertyId"
              element={
                <RequireAuth>
                  <DetailPage />
                </RequireAuth>
              }
            />
            <Route
              path="interest"
              element={
                <RequireAuth>
                  <InterestPage />
                </RequireAuth>
              }
            />
            <Route
              path="archived"
              element={
                <RequireAuth>
                  <ArchivedPage />
                </RequireAuth>
              }
            />
            <Route
              path="calendar"
              element={
                <RequireAuth>
                  <CalendarPage />
                </RequireAuth>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
