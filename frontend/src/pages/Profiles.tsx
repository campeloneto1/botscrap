import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getProfiles, createProfile, updateProfile, deleteProfile, testProfile, testProfileTelegram, getTelegramGroups, toggleProfile } from '../services/api'
import { Plus, Trash2, Play, Instagram, Pencil, X, Send, Pause, PlayCircle } from 'lucide-react'

export default function Profiles() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingProfile, setEditingProfile] = useState<any>(null)
  const [formData, setFormData] = useState({ platform: 'instagram', username: '', telegram_group_id: '', active: true })
  const [testResult, setTestResult] = useState<any>(null)

  const { data: profiles, isLoading } = useQuery({
    queryKey: ['profiles'],
    queryFn: getProfiles,
  })

  const { data: telegramGroups } = useQuery({
    queryKey: ['telegram-groups'],
    queryFn: getTelegramGroups,
  })

  const createMutation = useMutation({
    mutationFn: createProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profiles'] })
      handleCancel()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => updateProfile(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profiles'] })
      handleCancel()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profiles'] })
    },
  })

  const testMutation = useMutation({
    mutationFn: testProfile,
    onSuccess: (data) => {
      setTestResult({ ...data, type: 'scrape' })
    },
  })

  const testTelegramMutation = useMutation({
    mutationFn: testProfileTelegram,
    onSuccess: (data) => {
      setTestResult({ ...data, type: 'telegram' })
    },
  })

  const toggleMutation = useMutation({
    mutationFn: toggleProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profiles'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const data = {
      platform: formData.platform,
      username: formData.username,
      telegram_group_id: formData.telegram_group_id ? parseInt(formData.telegram_group_id) : undefined,
      active: formData.active,
    }

    if (editingProfile) {
      updateMutation.mutate({ id: editingProfile.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const handleEdit = (profile: any) => {
    setEditingProfile(profile)
    setFormData({
      platform: profile.platform,
      username: profile.username,
      telegram_group_id: profile.telegram_group_id?.toString() || '',
      active: profile.active,
    })
    setShowForm(true)
  }

  const handleCancel = () => {
    setEditingProfile(null)
    setFormData({ platform: 'instagram', username: '', telegram_group_id: '', active: true })
    setShowForm(false)
  }

  const platformIcons: Record<string, any> = {
    instagram: Instagram,
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Perfis Monitorados</h1>
        <button
          onClick={() => {
            setEditingProfile(null)
            setFormData({ platform: 'instagram', username: '', telegram_group_id: '', active: true })
            setShowForm(!showForm)
          }}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={20} />
          Adicionar Perfil
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium">
              {editingProfile ? 'Editar Perfil' : 'Novo Perfil'}
            </h3>
            <button onClick={handleCancel} className="text-gray-500 hover:text-gray-700">
              <X size={20} />
            </button>
          </div>
          <form onSubmit={handleSubmit} className="flex flex-wrap gap-4">
            <select
              value={formData.platform}
              onChange={(e) => setFormData({ ...formData, platform: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="instagram">Instagram</option>
              <option value="twitter" disabled>Twitter (em breve)</option>
              <option value="facebook" disabled>Facebook (em breve)</option>
            </select>

            <input
              type="text"
              placeholder="@username"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
              required
            />

            <select
              value={formData.telegram_group_id}
              onChange={(e) => setFormData({ ...formData, telegram_group_id: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">Selecione um grupo</option>
              {telegramGroups?.map((group: any) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>

            {editingProfile && (
              <label className="flex items-center gap-2 px-3 py-2">
                <input
                  type="checkbox"
                  checked={formData.active}
                  onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                  className="w-4 h-4"
                />
                Ativo
              </label>
            )}

            <button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              {createMutation.isPending || updateMutation.isPending ? 'Salvando...' : 'Salvar'}
            </button>
          </form>
        </div>
      )}

      {/* Test Result */}
      {testResult && (
        <div className={`p-4 rounded-lg mb-6 ${testResult.success ? 'bg-green-100' : 'bg-red-100'}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">
                {testResult.success
                  ? (testResult.type === 'telegram' ? 'Enviado para Telegram!' : 'Teste bem sucedido!')
                  : 'Erro no teste'}
              </p>
              {testResult.success ? (
                <div className="text-sm text-gray-600">
                  <p>Encontrados {testResult.posts_found} posts de @{testResult.profile}</p>
                  {testResult.type === 'telegram' && (
                    <>
                      <p>Enviados {testResult.posts_sent} posts para {testResult.telegram_group}</p>
                      {testResult.keywords_matched?.length > 0 && (
                        <p className="text-orange-600 font-medium">
                          Keywords encontradas: {testResult.keywords_matched.join(', ')}
                        </p>
                      )}
                    </>
                  )}
                </div>
              ) : (
                <p className="text-sm text-red-600">{testResult.error}</p>
              )}
            </div>
            <button onClick={() => setTestResult(null)} className="text-gray-500 hover:text-gray-700">
              Fechar
            </button>
          </div>
        </div>
      )}

      {/* Profiles List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : profiles?.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          Nenhum perfil cadastrado. Adicione seu primeiro perfil!
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Plataforma</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Username</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Grupo Telegram</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Status</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Ultimo Scrape</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {profiles?.map((profile: any) => {
                const Icon = platformIcons[profile.platform] || Instagram
                const hasTelegramGroup = !!profile.telegram_group_id
                return (
                  <tr key={profile.id}>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Icon size={20} className="text-pink-600" />
                        <span className="capitalize">{profile.platform}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-medium">@{profile.username}</td>
                    <td className="px-4 py-3 text-gray-500">
                      {telegramGroups?.find((g: any) => g.id === profile.telegram_group_id)?.name || '-'}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${
                          profile.active
                            ? 'bg-green-100 text-green-700'
                            : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {profile.active ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {profile.last_scraped
                        ? new Date(profile.last_scraped).toLocaleString('pt-BR')
                        : 'Nunca'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => toggleMutation.mutate(profile.id)}
                          disabled={toggleMutation.isPending}
                          className={`p-2 rounded-lg transition-colors ${
                            profile.active
                              ? 'text-orange-600 hover:bg-orange-50'
                              : 'text-green-600 hover:bg-green-50'
                          }`}
                          title={profile.active ? 'Pausar monitoramento' : 'Retomar monitoramento'}
                        >
                          {profile.active ? <Pause size={18} /> : <PlayCircle size={18} />}
                        </button>
                        <button
                          onClick={() => testMutation.mutate(profile.id)}
                          disabled={testMutation.isPending}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Testar scraping"
                        >
                          <Play size={18} />
                        </button>
                        {hasTelegramGroup && (
                          <button
                            onClick={() => testTelegramMutation.mutate(profile.id)}
                            disabled={testTelegramMutation.isPending}
                            className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                            title="Enviar para Telegram"
                          >
                            <Send size={18} />
                          </button>
                        )}
                        <button
                          onClick={() => handleEdit(profile)}
                          className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg transition-colors"
                          title="Editar"
                        >
                          <Pencil size={18} />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm('Tem certeza que deseja excluir este perfil?')) {
                              deleteMutation.mutate(profile.id)
                            }
                          }}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Excluir"
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
