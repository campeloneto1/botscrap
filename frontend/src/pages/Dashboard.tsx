import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getStats, getPosts, runManualScrape } from '../services/api'
import { Users, Hash, Send, FileText, AlertTriangle, Clock, Activity, Play, Loader2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useState } from 'react'

export default function Dashboard() {
  const { isAdmin, user } = useAuth()
  const queryClient = useQueryClient()
  const [scrapeResult, setScrapeResult] = useState<string | null>(null)

  // Debug - verificar no console do navegador (F12)
  console.log('Dashboard auth:', { user, isAdmin })

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
  })

  const scrapeMutation = useMutation({
    mutationFn: () => runManualScrape(3),
    onSuccess: (data) => {
      setScrapeResult(`Verificação concluída: ${data.posts_found} posts encontrados, ${data.posts_sent} enviados`)
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      queryClient.invalidateQueries({ queryKey: ['recent-posts'] })
      setTimeout(() => setScrapeResult(null), 5000)
    },
    onError: (error: any) => {
      setScrapeResult(`Erro: ${error.response?.data?.detail || error.message}`)
      setTimeout(() => setScrapeResult(null), 5000)
    },
  })

  const { data: recentPosts, isLoading: postsLoading } = useQuery({
    queryKey: ['recent-posts'],
    queryFn: () => getPosts({ limit: 10 }),
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

  const formatDateTime = (isoString: string | null) => {
    if (!isoString) return '-'
    return new Date(isoString).toLocaleString('pt-BR')
  }

  const scheduler = stats?.scheduler

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>

        {/* Scheduler Status */}
        {scheduler && (
          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-3 px-4 py-2 rounded-lg ${
              scheduler.is_running ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
            }`}>
              <div className="flex items-center gap-2">
                <Activity
                  size={18}
                  className={scheduler.is_running ? 'text-green-600 animate-pulse' : 'text-red-600'}
                />
                <span className={`font-medium ${scheduler.is_running ? 'text-green-700' : 'text-red-700'}`}>
                  {scheduler.is_running ? 'Scheduler Ativo' : 'Scheduler Parado'}
                </span>
              </div>
              {scheduler.is_running && scheduler.next_run && (
                <div className="flex items-center gap-1 text-sm text-gray-600 border-l border-gray-300 pl-3">
                  <Clock size={14} />
                  <span>Próxima verificação: {formatDateTime(scheduler.next_run)}</span>
                </div>
              )}
            </div>
            {isAdmin && (
              <button
                onClick={() => scrapeMutation.mutate()}
                disabled={scrapeMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {scrapeMutation.isPending ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Play size={18} />
                )}
                {scrapeMutation.isPending ? 'Verificando...' : 'Verificar Agora'}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Scrape Result Message */}
      {scrapeResult && (
        <div className={`mb-4 p-3 rounded-lg ${
          scrapeResult.startsWith('Erro') ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-green-50 text-green-700 border border-green-200'
        }`}>
          {scrapeResult}
        </div>
      )}

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
          ) : !recentPosts?.posts?.length ? (
            <p className="text-gray-500">Nenhum post coletado ainda.</p>
          ) : (
            <div className="space-y-4">
              {recentPosts.posts.map((post: any) => (
                <div
                  key={post.id}
                  className={`p-4 rounded-lg border ${
                    post.has_keyword ? 'border-red-200 bg-red-50' : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm text-gray-600 mb-1">
                        @{post.profile_username}
                      </p>
                      <p className="text-gray-800">
                        {post.summary || (post.content?.slice(0, 200) + (post.content?.length > 200 ? '...' : '')) || '(sem texto)'}
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
