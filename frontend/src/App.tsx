import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Posts from './pages/Posts'
import Profiles from './pages/Profiles'
import Keywords from './pages/Keywords'
import TelegramGroups from './pages/TelegramGroups'
import Settings from './pages/Settings'
import Users from './pages/Users'
import Layout from './components/Layout'
import { AuthProvider, useAuth } from './contexts/AuthContext'

function AppRoutes() {
  const { user, isAdmin, isLoading, setUser, refreshUser } = useAuth()

  const handleLogin = async () => {
    await refreshUser()
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  const isAuthenticated = !!user

  return (
    <Routes>
      <Route
        path="/login"
        element={
          isAuthenticated ? (
            <Navigate to="/" replace />
          ) : (
            <Login onLogin={handleLogin} />
          )
        }
      />
      <Route
        path="/"
        element={
          isAuthenticated ? (
            <Layout onLogout={handleLogout} isAdmin={isAdmin}>
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
            <Layout onLogout={handleLogout} isAdmin={isAdmin}>
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
            <Layout onLogout={handleLogout} isAdmin={isAdmin}>
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
            <Layout onLogout={handleLogout} isAdmin={isAdmin}>
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
            <Layout onLogout={handleLogout} isAdmin={isAdmin}>
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
            isAdmin ? (
              <Layout onLogout={handleLogout} isAdmin={isAdmin}>
                <Users />
              </Layout>
            ) : (
              <Navigate to="/" replace />
            )
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      <Route
        path="/settings"
        element={
          isAuthenticated ? (
            isAdmin ? (
              <Layout onLogout={handleLogout} isAdmin={isAdmin}>
                <Settings />
              </Layout>
            ) : (
              <Navigate to="/" replace />
            )
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
