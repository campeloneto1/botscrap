import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Users, Hash, Send, LogOut } from 'lucide-react'

interface LayoutProps {
  children: React.ReactNode
  onLogout: () => void
}

export default function Layout({ children, onLogout }: LayoutProps) {
  const location = useLocation()

  const handleLogout = () => {
    localStorage.removeItem('token')
    onLogout()
  }

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/profiles', label: 'Perfis', icon: Users },
    { path: '/keywords', label: 'Palavras-chave', icon: Hash },
    { path: '/telegram', label: 'Telegram', icon: Send },
  ]

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 text-white">
        <div className="p-4">
          <h1 className="text-xl font-bold">BotScrap</h1>
          <p className="text-gray-400 text-sm">Social Media Monitor</p>
        </div>

        <nav className="mt-8">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800'
                }`}
              >
                <Icon size={20} />
                {item.label}
              </Link>
            )
          })}
        </nav>

        <div className="absolute bottom-0 w-64 p-4">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 text-gray-300 hover:text-white transition-colors"
          >
            <LogOut size={20} />
            Sair
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 p-8 overflow-auto">
        {children}
      </main>
    </div>
  )
}
