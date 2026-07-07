import { Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Users, Hash, Send, LogOut, FileText, Settings, UserCog } from 'lucide-react'

interface LayoutProps {
  children: React.ReactNode
  onLogout: () => void
  isAdmin: boolean
}

export default function Layout({ children, onLogout, isAdmin }: LayoutProps) {
  const location = useLocation()

  const handleLogout = () => {
    localStorage.removeItem('token')
    onLogout()
  }

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard, adminOnly: false },
    { path: '/posts', label: 'Posts', icon: FileText, adminOnly: false },
    { path: '/profiles', label: 'Perfis', icon: Users, adminOnly: false },
    { path: '/keywords', label: 'Palavras-chave', icon: Hash, adminOnly: false },
    { path: '/telegram', label: 'Telegram', icon: Send, adminOnly: false },
    { path: '/users', label: 'Usuários', icon: UserCog, adminOnly: true },
    { path: '/settings', label: 'Configurações', icon: Settings, adminOnly: true },
  ]

  const visibleNavItems = navItems.filter(item => !item.adminOnly || isAdmin)

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 text-white">
        <div className="p-4">
          <h1 className="text-xl font-bold">BotScrap</h1>
          <p className="text-gray-400 text-sm">Social Media Monitor</p>
        </div>

        <nav className="mt-8">
          {visibleNavItems.map((item) => {
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
