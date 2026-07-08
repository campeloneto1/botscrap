import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAppSettings, updateAppSettings, testTelegramConnection, AppSettings } from '../services/api'
import { Save, RefreshCw, CheckCircle, XCircle, Eye, EyeOff } from 'lucide-react'

export default function Settings() {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState<Partial<AppSettings>>({})
  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({})
  const [testResult, setTestResult] = useState<any>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: getAppSettings,
  })

  useEffect(() => {
    if (settings) {
      setFormData(settings)
    }
  }, [settings])

  const updateMutation = useMutation({
    mutationFn: updateAppSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    },
  })

  const testTelegramMutation = useMutation({
    mutationFn: testTelegramConnection,
    onSuccess: (data) => {
      setTestResult(data)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate(formData)
  }

  const togglePasswordVisibility = (field: string) => {
    setShowPasswords(prev => ({ ...prev, [field]: !prev[field] }))
  }

  const isMasked = (value: string | null | undefined) => {
    return value?.startsWith('*')
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold mb-6">Configurações</h1>

      {saveSuccess && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-green-700">
          <CheckCircle size={20} />
          Configurações salvas com sucesso!
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Telegram Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">🤖</span> Telegram Bot
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Bot Token
              </label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <input
                    type={showPasswords['telegram_bot_token'] ? 'text' : 'password'}
                    value={formData.telegram_bot_token || ''}
                    onChange={(e) => setFormData({ ...formData, telegram_bot_token: e.target.value })}
                    placeholder={isMasked(settings?.telegram_bot_token) ? 'Token configurado (deixe em branco para manter)' : 'Cole o token do @BotFather'}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => togglePasswordVisibility('telegram_bot_token')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPasswords['telegram_bot_token'] ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => testTelegramMutation.mutate()}
                  disabled={testTelegramMutation.isPending}
                  className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors disabled:opacity-50"
                >
                  {testTelegramMutation.isPending ? <RefreshCw className="animate-spin" size={18} /> : 'Testar'}
                </button>
              </div>
              {testResult && (
                <div className={`mt-2 text-sm flex items-center gap-1 ${testResult.success ? 'text-green-600' : 'text-red-600'}`}>
                  {testResult.success ? (
                    <>
                      <CheckCircle size={14} />
                      Conectado: @{testResult.bot_username} ({testResult.bot_name})
                    </>
                  ) : (
                    <>
                      <XCircle size={14} />
                      {testResult.error}
                    </>
                  )}
                </div>
              )}
              <p className="mt-1 text-xs text-gray-500">
                Obtenha um token em @BotFather no Telegram
              </p>
            </div>
          </div>
        </div>

        {/* Instagram Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">📸</span> Instagram (Opcional)
          </h2>
          <p className="text-sm text-gray-500 mb-4">
            Credenciais para melhorar o scraping (evita rate limits)
          </p>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username
              </label>
              <input
                type="text"
                value={formData.instagram_username || ''}
                onChange={(e) => setFormData({ ...formData, instagram_username: e.target.value })}
                placeholder="@usuario"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPasswords['instagram_password'] ? 'text' : 'password'}
                  value={formData.instagram_password || ''}
                  onChange={(e) => setFormData({ ...formData, instagram_password: e.target.value })}
                  placeholder={isMasked(settings?.instagram_password) ? '******' : 'Senha'}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg pr-10"
                />
                <button
                  type="button"
                  onClick={() => togglePasswordVisibility('instagram_password')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPasswords['instagram_password'] ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Twitter Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">𝕏</span> Twitter/X (Obrigatório)
          </h2>
          <p className="text-sm text-gray-500 mb-4">
            Twitter agora requer login para ver a maioria do conteúdo
          </p>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username
              </label>
              <input
                type="text"
                value={formData.twitter_username || ''}
                onChange={(e) => setFormData({ ...formData, twitter_username: e.target.value })}
                placeholder="@usuario ou email"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPasswords['twitter_password'] ? 'text' : 'password'}
                  value={formData.twitter_password || ''}
                  onChange={(e) => setFormData({ ...formData, twitter_password: e.target.value })}
                  placeholder={isMasked(settings?.twitter_password) ? '******' : 'Senha'}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg pr-10"
                />
                <button
                  type="button"
                  onClick={() => togglePasswordVisibility('twitter_password')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPasswords['twitter_password'] ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Facebook Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">📘</span> Facebook (Obrigatório)
          </h2>
          <p className="text-sm text-gray-500 mb-4">
            Use email ao invés de username para login
          </p>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                type="email"
                value={formData.facebook_email || ''}
                onChange={(e) => setFormData({ ...formData, facebook_email: e.target.value })}
                placeholder="email@example.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPasswords['facebook_password'] ? 'text' : 'password'}
                  value={formData.facebook_password || ''}
                  onChange={(e) => setFormData({ ...formData, facebook_password: e.target.value })}
                  placeholder={isMasked(settings?.facebook_password) ? '******' : 'Senha'}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg pr-10"
                />
                <button
                  type="button"
                  onClick={() => togglePasswordVisibility('facebook_password')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPasswords['facebook_password'] ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Scraping Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">⏱️</span> Scraping
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Intervalo de verificação (horas)
              </label>
              <input
                type="number"
                min="1"
                max="24"
                value={formData.scrape_interval_hours || 6}
                onChange={(e) => setFormData({ ...formData, scrape_interval_hours: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
              <p className="mt-1 text-xs text-gray-500">
                A cada quantas horas verificar novos posts
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Delay entre perfis (segundos)
              </label>
              <input
                type="number"
                min="1"
                max="60"
                value={formData.scrape_delay_seconds || 3}
                onChange={(e) => setFormData({ ...formData, scrape_delay_seconds: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
              <p className="mt-1 text-xs text-gray-500">
                Tempo de espera entre cada perfil (evita bloqueio)
              </p>
            </div>
          </div>
        </div>

        {/* AI Summary Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">🤖</span> Resumo com IA (Groq)
          </h2>

          <div className="space-y-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.enable_ai_summary || false}
                onChange={(e) => setFormData({ ...formData, enable_ai_summary: e.target.checked })}
                className="w-4 h-4 rounded border-gray-300"
              />
              <span className="text-sm">Ativar resumo automático de posts longos</span>
            </label>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Groq API Key
              </label>
              <div className="relative">
                <input
                  type={showPasswords['groq_api_key'] ? 'text' : 'password'}
                  value={formData.groq_api_key || ''}
                  onChange={(e) => setFormData({ ...formData, groq_api_key: e.target.value })}
                  placeholder={isMasked(settings?.groq_api_key) ? 'API Key configurada' : 'gsk_...'}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg pr-10"
                />
                <button
                  type="button"
                  onClick={() => togglePasswordVisibility('groq_api_key')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPasswords['groq_api_key'] ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Obtenha gratuitamente em{' '}
                <a href="https://console.groq.com" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                  console.groq.com
                </a>
              </p>
            </div>
          </div>
        </div>

        {/* Proxies Section */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">🌐</span> Proxies (Avançado)
          </h2>

          <div className="space-y-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.use_proxies || false}
                onChange={(e) => setFormData({ ...formData, use_proxies: e.target.checked })}
                className="w-4 h-4 rounded border-gray-300"
              />
              <span className="text-sm">Usar proxies para scraping</span>
            </label>

            {formData.use_proxies && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Lista de Proxies (um por linha)
                </label>
                <textarea
                  value={formData.proxy_list || ''}
                  onChange={(e) => setFormData({ ...formData, proxy_list: e.target.value })}
                  placeholder="http://user:pass@host:port&#10;http://host2:port2"
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm"
                />
              </div>
            )}
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={updateMutation.isPending}
            className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {updateMutation.isPending ? (
              <RefreshCw className="animate-spin" size={18} />
            ) : (
              <Save size={18} />
            )}
            Salvar Configurações
          </button>
        </div>
      </form>
    </div>
  )
}
