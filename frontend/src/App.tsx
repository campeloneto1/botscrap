import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Posts from './pages/Posts'
import Profiles from './pages/Profiles'
import Keywords from './pages/Keywords'
import TelegramGroups from './pages/TelegramGroups'
import Settings from './pages/Settings'
import Users from './pages/Users'
import Layout from './components/Layout'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('token')
    setIsAuthenticated(!!token)
  }, [])

  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            isAuthenticated ? (
              <Navigate to="/" replace />
            ) : (
              <Login onLogin={() => setIsAuthenticated(true)} />
            )
          }
        />
        <Route
          path="/"
          element={
            isAuthenticated ? (
              <Layout onLogout={() => setIsAuthenticated(false)}>
                <Dashboard />
              </Layout>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route
          path="/posts"
          element={
            isAuthenticated ? (
              <Layout onLogout={() => setIsAuthenticated(false)}>
                <Posts />
              </Layout>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route
          path="/profiles"
          element={
            isAuthenticated ? (
              <Layout onLogout={() => setIsAuthenticated(false)}>
                <Profiles />
              </Layout>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route
          path="/keywords"
          element={
            isAuthenticated ? (
              <Layout onLogout={() => setIsAuthenticated(false)}>
                <Keywords />
              </Layout>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route
          path="/telegram"
          element={
            isAuthenticated ? (
              <Layout onLogout={() => setIsAuthenticated(false)}>
                <TelegramGroups />
              </Layout>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route
          path="/users"
          element={
            isAuthenticated ? (
              <Layout onLogout={() => setIsAuthenticated(false)}>
                <Users />
              </Layout>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route
          path="/settings"
          element={
            isAuthenticated ? (
              <Layout onLogout={() => setIsAuthenticated(false)}>
                <Settings />
              </Layout>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App
