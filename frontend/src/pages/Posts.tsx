import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { searchPosts, exportPosts, getProfiles } from '../services/api'
import { Search, Download, Filter, X, ExternalLink, Instagram } from 'lucide-react'

export default function Posts() {
  const [filters, setFilters] = useState({
    query: '',
    platform: '',
    profile_id: undefined as number | undefined,
    status: '',
    has_keyword: undefined as boolean | undefined,
    date_from: '',
    date_to: '',
  })
  const [activeFilters, setActiveFilters] = useState(filters)
  const [showFilters, setShowFilters] = useState(false)
  const [page, setPage] = useState(0)
  const limit = 20

  const { data: profiles } = useQuery({
    queryKey: ['profiles'],
    queryFn: getProfiles,
  })

  const { data, isLoading } = useQuery({
    queryKey: ['search-posts', activeFilters, page],
    queryFn: () =>
      searchPosts({
        ...activeFilters,
        limit,
        offset: page * limit,
      }),
  })

  const handleSearch = () => {
    setActiveFilters(filters)
    setPage(0)
  }

  const handleExport = async () => {
    await exportPosts(activeFilters)
  }

  const clearFilters = () => {
    const clearedFilters = {
      query: '',
      platform: '',
      profile_id: undefined,
      status: '',
      has_keyword: undefined,
      date_from: '',
      date_to: '',
    }
    setFilters(clearedFilters)
    setActiveFilters(clearedFilters)
    setPage(0)
  }

  const totalPages = data?.total ? Math.ceil(data.total / limit) : 0

  const platformIcons: Record<string, any> = {
    instagram: Instagram,
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Histórico de Posts</h1>
        <button
          onClick={handleExport}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          <Download size={18} />
          Exportar CSV
        </button>
      </div>

      {/* Search Bar */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex gap-3">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Buscar por palavra-chave, texto, OCR..."
              value={filters.query}
              onChange={(e) => setFilters({ ...filters, query: e.target.value })}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={handleSearch}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
          >
            <Search size={18} />
            Buscar
          </button>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
              showFilters ? 'bg-gray-700 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            <Filter size={18} />
            Filtros
          </button>
        </div>

        {/* Advanced Filters */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Plataforma</label>
              <select
                value={filters.platform}
                onChange={(e) => setFilters({ ...filters, platform: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todas</option>
                <option value="instagram">Instagram</option>
                <option value="twitter">Twitter</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Perfil</label>
              <select
                value={filters.profile_id || ''}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    profile_id: e.target.value ? parseInt(e.target.value) : undefined,
                  })
                }
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos</option>
                {profiles?.profiles?.map((p: any) => (
                  <option key={p.id} value={p.id}>
                    @{p.username} ({p.platform})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos</option>
                <option value="pending">Pendente</option>
                <option value="processing">Processando</option>
                <option value="completed">Completo</option>
                <option value="failed">Falhou</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Keywords</label>
              <select
                value={filters.has_keyword === undefined ? '' : filters.has_keyword.toString()}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    has_keyword: e.target.value === '' ? undefined : e.target.value === 'true',
                  })
                }
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Todos</option>
                <option value="true">Com keywords</option>
                <option value="false">Sem keywords</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Data Inicial</label>
              <input
                type="date"
                value={filters.date_from}
                onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Data Final</label>
              <input
                type="date"
                value={filters.date_to}
                onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-end lg:col-span-2">
              <button
                onClick={clearFilters}
                className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors flex items-center justify-center gap-2"
              >
                <X size={18} />
                Limpar Filtros
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Results count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">{data?.total || 0} posts encontrados</p>
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : !data?.posts?.length ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          Nenhum post encontrado.
        </div>
      ) : (
        <div className="space-y-4">
          {data.posts.map((post: any) => {
            const Icon = platformIcons[post.profile?.platform] || Instagram
            return (
              <div
                key={post.id}
                className={`bg-white rounded-lg shadow p-4 ${
                  post.has_keyword ? 'border-l-4 border-red-500' : ''
                }`}
              >
                <div className="flex items-start gap-4">
                  {/* Profile info */}
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-pink-100 rounded-full flex items-center justify-center">
                      <Icon size={20} className="text-pink-600" />
                    </div>
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="font-medium">@{post.profile?.username}</span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded ${
                          post.status === 'completed'
                            ? 'bg-green-100 text-green-700'
                            : post.status === 'failed'
                            ? 'bg-red-100 text-red-700'
                            : post.status === 'processing'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        {post.status}
                      </span>
                      {post.sent_at && (
                        <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                          Enviado
                        </span>
                      )}
                      {post.has_keyword && (
                        <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">
                          Alerta
                        </span>
                      )}
                    </div>

                    {/* Summary */}
                    {post.summary && (
                      <div className="mb-2 p-2 bg-blue-50 rounded text-sm">
                        <span className="text-blue-600 font-medium">Resumo IA: </span>
                        <span className="text-gray-700">{post.summary}</span>
                      </div>
                    )}

                    {/* Content */}
                    <p className="text-gray-800 whitespace-pre-wrap mb-2">{post.content || '(sem texto)'}</p>

                    {/* OCR */}
                    {post.ocr_text && (
                      <div className="mb-2 p-2 bg-purple-50 rounded text-sm">
                        <span className="text-purple-600 font-medium">OCR: </span>
                        <span className="text-gray-700">
                          {post.ocr_text.slice(0, 200)}
                          {post.ocr_text.length > 200 && '...'}
                        </span>
                      </div>
                    )}

                    {/* Keywords */}
                    {post.has_keyword && post.matched_keywords && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {post.matched_keywords.map((kw: string) => (
                          <span key={kw} className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">
                            {kw}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Footer */}
                    <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                      <span>{post.processed_at ? new Date(post.processed_at).toLocaleString('pt-BR') : ''}</span>
                      <a
                        href={`https://instagram.com/p/${post.post_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-blue-600 hover:text-blue-800"
                      >
                        Ver original <ExternalLink size={12} />
                      </a>
                    </div>
                  </div>

                  {/* Media thumbnail */}
                  {post.media_url && (
                    <div className="flex-shrink-0">
                      <img
                        src={post.media_url}
                        alt=""
                        className="w-20 h-20 object-cover rounded-lg"
                        onError={(e) => {
                          ;(e.target as HTMLImageElement).style.display = 'none'
                        }}
                      />
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between p-4 bg-white rounded-lg shadow">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Anterior
          </button>
          <span className="text-sm text-gray-600">
            Página {page + 1} de {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
            disabled={page >= totalPages - 1}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Próxima
          </button>
        </div>
      )}
    </div>
  )
}
