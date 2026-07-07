import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { getMe, User } from '../services/api'

interface AuthContextType {
  user: User | null
  isAdmin: boolean
  isLoading: boolean
  setUser: (user: User | null) => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshUser = async () => {
    const token = localStorage.getItem('token')
    if (!token) {
      setUser(null)
      setIsLoading(false)
      return
    }

    try {
      const userData = await getMe()
      setUser(userData)
    } catch {
      setUser(null)
      localStorage.removeItem('token')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    refreshUser()
  }, [])

  const isAdmin = user?.is_admin ?? false

  return (
    <AuthContext.Provider value={{ user, isAdmin, isLoading, setUser, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
