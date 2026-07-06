import { useQuery } from '@tanstack/react-query'
import { getStats, getPosts } from '../services/api'
import { Users, Hash, Send, FileText, AlertTriangle } from 'lucide-react'

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
  })

  const { data: recentPosts, isLoading: postsLoading } = useQuery({
    queryKey: ['recent-posts'],
    queryFn: () => getPosts(10),
  })

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  const statCards = [
    { label: 'Perfis Ativos', value: stats?.active_profiles || 0, icon: Users, color: 'bg-blue-500' },
    { label: 'Palavras-chave', value: stats?.total_keywords || 0, icon: Hash, color: 'bg-green-500' },
    { label: 'Grupos Telegram', value: stats?.total_telegram_groups || 0, icon: Send, color: 'bg-purple-500' },
    { label: 'Posts Hoje', value: stats?.posts_today || 0, icon: FileText, color: 'bg-orange-500' },
    { label: 'Alertas Hoje', value: stats?.keyword_alerts_today || 0, icon: AlertTriangle, color: 'bg-red-500' },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        {statCards.map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.label} className="bg-white rounded-lg shadow p-4">
              <div className="flex items-center gap-3">
                <div className={`${stat.color} p-2 rounded-lg`}>
                  <Icon className="text-white" size={20} />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stat.value}</p>
                  <p className="text-sm text-gray-500">{stat.label}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Recent Posts */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold">Posts Recentes</h2>
        </div>
        <div className="p-4">
          {postsLoading ? (
            <p className="text-gray-500">Carregando...</p>
          ) : recentPosts?.length === 0 ? (
            <p className="text-gray-500">Nenhum post coletado ainda.</p>
          ) : (
            <div className="space-y-4">
              {recentPosts?.map((post: any) => (
                <div
                  key={post.id}
                  className={`p-4 rounded-lg border ${
                    post.has_keyword ? 'border-red-200 bg-red-50' : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm text-gray-600 mb-1">
                        Post ID: {post.post_id}
                      </p>
                      <p className="text-gray-800">
                        {post.content || '(sem texto)'}
                      </p>
                      {post.has_keyword && post.matched_keywords && (
                        <div className="mt-2">
                          <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">
                            Palavras: {post.matched_keywords.join(', ')}
                          </span>
                        </div>
                      )}
                    </div>
                    <span className="text-xs text-gray-400">
                      {new Date(post.processed_at).toLocaleString('pt-BR')}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
