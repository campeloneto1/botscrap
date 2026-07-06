import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getPosts, getProfiles, PostsFilter } from '../services/api'
import { Search, ChevronLeft, ChevronRight, ExternalLink, Instagram } from 'lucide-react'

export default function Posts() {
  const [filters, setFilters] = useState<PostsFilter>({
    limit: 20,
    offset: 0,
  })
  const [searchInput, setSearchInput] = useState('')

  const { data: postsData, isLoading } = useQuery({
    queryKey: ['posts', filters],
    queryFn: () => getPosts(filters),
  })

  const { data: profiles } = useQuery({
    queryKey: ['profiles'],
    queryFn: getProfiles,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setFilters({ ...filters, search: searchInput, offset: 0 })
  }

  const handleFilterChange = (key: keyof PostsFilter, value: any) => {
    setFilters({ ...filters, [key]: value, offset: 0 })
  }

  const handlePageChange = (direction: 'prev' | 'next') => {
    const newOffset = direction === 'next'
      ? (filters.offset || 0) + (filters.limit || 20)
      : Math.max(0, (filters.offset || 0) - (filters.limit || 20))
    setFilters({ ...filters, offset: newOffset })
  }

  const currentPage = Math.floor((filters.offset || 0) / (filters.limit || 20)) + 1
  const totalPages = Math.ceil((postsData?.total || 0) / (filters.limit || 20))

  const platformIcons: Record<string, any> = {
    instagram: Instagram,
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Posts Coletados</h1>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-wrap items-center gap-4">
          {/* Search */}
          <form onSubmit={handleSearch} className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              <input
                type="text"
                placeholder="Buscar no conteúdo..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </form>

          {/* Profile Filter */}
          <select
            value={filters.profile_id || ''}
            onChange={(e) => handleFilterChange('profile_id', e.target.value ? parseInt(e.target.value) : undefined)}
            className="px-3 py-2 border border-gray-300 rounded-lg"
          >
            <option value="">Todos os perfis</option>
            {profiles?.map((profile: any) => (
              <option key={profile.id} value={profile.id}>
                @{profile.username}
              </option>
            ))}
          </select>

          {/* Keyword Only */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filters.keyword_only || false}
              onChange={(e) => handleFilterChange('keyword_only', e.target.checked)}
              className="w-4 h-4 rounded border-gray-300"
            />
            <span className="text-sm">Com palavras-chave</span>
          </label>

          {/* Sent Only */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filters.sent_only || false}
              onChange={(e) => handleFilterChange('sent_only', e.target.checked)}
              className="w-4 h-4 rounded border-gray-300"
            />
            <span className="text-sm">Enviados</span>
          </label>

          {/* Clear Filters */}
          {(filters.search || filters.profile_id || filters.keyword_only || filters.sent_only) && (
            <button
              onClick={() => {
                setFilters({ limit: 20, offset: 0 })
                setSearchInput('')
              }}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Limpar filtros
            </button>
          )}
        </div>
      </div>

      {/* Results count */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-600">
          {postsData?.total || 0} posts encontrados
        </p>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">Por página:</span>
          <select
            value={filters.limit || 20}
            onChange={(e) => handleFilterChange('limit', parseInt(e.target.value))}
            className="px-2 py-1 border border-gray-300 rounded text-sm"
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
          </select>
        </div>
      </div>

      {/* Posts List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : !postsData?.posts?.length ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          Nenhum post encontrado com os filtros selecionados.
        </div>
      ) : (
        <div className="space-y-4">
          {postsData.posts.map((post: any) => {
            const Icon = platformIcons[post.profile_platform] || Instagram
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
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium">@{post.profile_username}</span>
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

                    {/* Summary or Content */}
                    {post.summary && (
                      <div className="mb-2">
                        <span className="text-xs text-blue-600 font-medium">Resumo IA: </span>
                        <span className="text-gray-700">{post.summary}</span>
                      </div>
                    )}

                    <p className="text-gray-800 whitespace-pre-wrap">
                      {post.summary
                        ? (post.content?.length > 300
                          ? post.content.slice(0, 300) + '...'
                          : post.content)
                        : post.content || '(sem texto)'}
                    </p>

                    {/* Keywords */}
                    {post.has_keyword && post.matched_keywords && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {post.matched_keywords.map((kw: string) => (
                          <span
                            key={kw}
                            className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded"
                          >
                            {kw}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Footer */}
                    <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                      <span>{new Date(post.processed_at).toLocaleString('pt-BR')}</span>
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
                          (e.target as HTMLImageElement).style.display = 'none'
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
        <div className="flex items-center justify-center gap-4 mt-6">
          <button
            onClick={() => handlePageChange('prev')}
            disabled={currentPage === 1}
            className="flex items-center gap-1 px-3 py-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            <ChevronLeft size={18} />
            Anterior
          </button>
          <span className="text-sm text-gray-600">
            Página {currentPage} de {totalPages}
          </span>
          <button
            onClick={() => handlePageChange('next')}
            disabled={currentPage === totalPages}
            className="flex items-center gap-1 px-3 py-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Próxima
            <ChevronRight size={18} />
          </button>
        </div>
      )}
    </div>
  )
}
