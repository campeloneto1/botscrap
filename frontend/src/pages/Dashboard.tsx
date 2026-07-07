import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getStats,
  runManualScrape,
  getScrapeStatus,
  getStatsOverview,
  getPostsTimeline,
  getRecentPosts,
  getHealthStatus,
  getFailedPosts,
  retryFailedPosts,
} from '../services/api'
import {
  Users,
  Hash,
  Send,
  FileText,
  AlertTriangle,
  Clock,
  Activity,
  Play,
  Loader2,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  XCircle,
  RefreshCcw,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useState, useEffect } from 'react'

export default function Dashboard() {
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [scrapeResult, setScrapeResult] = useState<string | null>(null)
  const [isScrapingBackground, setIsScrapingBackground] = useState(false)

  // Old stats (for scheduler status)
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
    refetchInterval: isScrapingBackground ? 3000 : false,
  })

  // New stats overview
  const { data: overview } = useQuery({
    queryKey: ['stats-overview'],
    queryFn: getStatsOverview,
    refetchInterval: 30000, // Refresh every 30s
  })

  // Timeline data
  const { data: timeline } = useQuery({
    queryKey: ['stats-timeline'],
    queryFn: () => getPostsTimeline(7),
    refetchInterval: 60000, // Refresh every minute
  })

  // Recent posts with keywords
  const { data: recentPostsData } = useQuery({
    queryKey: ['stats-recent-posts'],
    queryFn: () => getRecentPosts(10),
    refetchInterval: 30000,
  })

  // Health status
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: getHealthStatus,
    refetchInterval: 60000,
  })

  // Failed posts
  const { data: failedPosts } = useQuery({
    queryKey: ['failed-posts'],
    queryFn: () => getFailedPosts(10),
  })

  // Check if scraping is running from stats
  useEffect(() => {
    if (stats?.scheduler?.manual_scrape_running) {
      setIsScrapingBackground(true)
    }
  }, [stats?.scheduler?.manual_scrape_running])

  // Poll scrape status while running
  const { data: scrapeStatus } = useQuery({
    queryKey: ['scrape-status'],
    queryFn: getScrapeStatus,
    refetchInterval: isScrapingBackground ? 2000 : false,
    enabled: isScrapingBackground,
  })

  // Check when scraping finishes
  useEffect(() => {
    if (isScrapingBackground && scrapeStatus && !scrapeStatus.running) {
      setIsScrapingBackground(false)
      if (scrapeStatus.result) {
        if (scrapeStatus.result.success !== false) {
          setScrapeResult(
            `Verificação concluída: ${scrapeStatus.result.posts_found || 0} posts encontrados`
          )
        } else {
          setScrapeResult(`Erro: ${scrapeStatus.result.error}`)
        }
        queryClient.invalidateQueries({ queryKey: ['stats'] })
        queryClient.invalidateQueries({ queryKey: ['stats-overview'] })
        queryClient.invalidateQueries({ queryKey: ['stats-recent-posts'] })
        queryClient.invalidateQueries({ queryKey: ['stats-timeline'] })
        setTimeout(() => setScrapeResult(null), 5000)
      }
    }
  }, [scrapeStatus, isScrapingBackground, queryClient])

  const scrapeMutation = useMutation({
    mutationFn: () => runManualScrape(3),
    onSuccess: () => {
      setIsScrapingBackground(true)
      setScrapeResult('Verificação iniciada em background...')
    },
    onError: (error: any) => {
      setScrapeResult(`Erro: ${error.response?.data?.detail || error.message}`)
      setTimeout(() => setScrapeResult(null), 5000)
    },
  })

  const retryMutation = useMutation({
    mutationFn: () => retryFailedPosts(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['failed-posts'] })
      queryClient.invalidateQueries({ queryKey: ['stats-overview'] })
      setScrapeResult(`${data.count} posts marcados para reprocessamento`)
      setTimeout(() => setScrapeResult(null), 5000)
    },
    onError: (error: any) => {
      setScrapeResult(`Erro ao reprocessar: ${error.response?.data?.detail || error.message}`)
      setTimeout(() => setScrapeResult(null), 5000)
    },
  })

  const formatDateTime = (isoString: string | null) => {
    if (!isoString) return '-'
    return new Date(isoString).toLocaleString('pt-BR')
  }

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  const scheduler = stats?.scheduler
  const statusCounts = overview?.status_counts || {}

  // Status cards
  const statusCards = [
    {
      label: 'Pendentes',
      value: statusCounts.pending || 0,
      icon: Clock,
      color: 'bg-yellow-500',
    },
    {
      label: 'Processando',
      value: statusCounts.processing || 0,
      icon: Loader2,
      color: 'bg-blue-500',
    },
    {
      label: 'Completados',
      value: statusCounts.completed || 0,
      icon: CheckCircle,
      color: 'bg-green-500',
    },
    {
      label: 'Falhados',
      value: statusCounts.failed || 0,
      icon: XCircle,
      color: 'bg-red-500',
    },
  ]

  // Summary cards
  const summaryCards = [
    {
      label: 'Total de Posts',
      value: overview?.total_posts || 0,
      icon: FileText,
      color: 'bg-purple-500',
    },
    {
      label: 'Keywords (7 dias)',
      value: overview?.keywords_last_7_days || 0,
      icon: AlertTriangle,
      color: 'bg-orange-500',
    },
    {
      label: 'OCR Processados',
      value: overview?.ocr_processed || 0,
      icon: TrendingUp,
      color: 'bg-indigo-500',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>

        {/* Scheduler Status */}
        {scheduler && (
          <div className="flex items-center gap-3">
            <div
              className={`flex items-center gap-3 px-4 py-2 rounded-lg ${
                scheduler.is_running
                  ? 'bg-green-50 border border-green-200'
                  : 'bg-red-50 border border-red-200'
              }`}
            >
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
                  <span>Próxima: {formatDateTime(scheduler.next_run)}</span>
                </div>
              )}
            </div>
            {isAdmin && (
              <button
                onClick={() => scrapeMutation.mutate()}
                disabled={scrapeMutation.isPending || isScrapingBackground}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {scrapeMutation.isPending || isScrapingBackground ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Play size={18} />
                )}
                {isScrapingBackground ? 'Verificando...' : scrapeMutation.isPending ? 'Iniciando...' : 'Verificar Agora'}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Messages */}
      {scrapeResult && (
        <div
          className={`p-3 rounded-lg ${
            scrapeResult.startsWith('Erro')
              ? 'bg-red-50 text-red-700 border border-red-200'
              : 'bg-green-50 text-green-700 border border-green-200'
          }`}
        >
          {scrapeResult}
        </div>
      )}

      {/* Health Status */}
      {health && health.status !== 'healthy' && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle size={20} className="text-yellow-600" />
            <span className="font-semibold text-yellow-800">Status do Sistema: {health.status}</span>
          </div>
          <div className="text-sm text-yellow-700 space-y-1">
            {Object.entries(health.components || {}).map(([name, comp]: [string, any]) => (
              comp.status !== 'healthy' && (
                <div key={name}>
                  <strong>{name}:</strong> {comp.message}
                </div>
              )
            ))}
          </div>
        </div>
      )}

      {/* Status Grid */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Status de Processamento</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {statusCards.map((stat) => {
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
      </div>

      {/* Summary Grid */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Resumo</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {summaryCards.map((stat) => {
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
      </div>

      {/* Failed Posts */}
      {failedPosts && failedPosts.total > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b flex items-center justify-between">
            <h2 className="text-lg font-semibold text-red-600">Posts com Falha ({failedPosts.total})</h2>
            <button
              onClick={() => retryMutation.mutate()}
              disabled={retryMutation.isPending}
              className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {retryMutation.isPending ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <RefreshCcw size={16} />
              )}
              Reprocessar Todos
            </button>
          </div>
          <div className="p-4 space-y-3">
            {failedPosts.posts?.slice(0, 5).map((post: any) => (
              <div key={post.id} className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium text-gray-800">
                      @{post.profile?.username} ({post.profile?.platform})
                    </p>
                    <p className="text-gray-600 mt-1">{post.content}</p>
                  </div>
                  <span className="text-xs text-gray-500">
                    {post.processed_at ? new Date(post.processed_at).toLocaleString('pt-BR') : ''}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Posts with Keywords */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold">Posts Recentes</h2>
        </div>
        <div className="p-4">
          {!recentPostsData?.posts?.length ? (
            <p className="text-gray-500">Nenhum post processado ainda.</p>
          ) : (
            <div className="space-y-4">
              {recentPostsData.posts.map((post: any) => (
                <div
                  key={post.id}
                  className={`p-4 rounded-lg border ${
                    post.has_keyword ? 'border-red-200 bg-red-50' : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm text-gray-600 mb-1">
                        @{post.profile?.username} ({post.profile?.platform})
                      </p>
                      <p className="text-gray-800">{post.content}</p>
                      {post.has_keyword && post.matched_keywords && (
                        <div className="mt-2">
                          <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">
                            Palavras: {post.matched_keywords.join(', ')}
                          </span>
                        </div>
                      )}
                    </div>
                    <span className="text-xs text-gray-400">
                      {post.processed_at ? new Date(post.processed_at).toLocaleString('pt-BR') : ''}
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
