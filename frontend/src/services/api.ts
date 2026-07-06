import axios from 'axios'

const API_URL = '/api'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 errors - only redirect if we had a token (meaning it expired)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const hadToken = localStorage.getItem('token')
      localStorage.removeItem('token')
      // Only redirect if we're not already on login page and had a token
      if (hadToken && !window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Auth
export const login = async (email: string, password: string) => {
  const formData = new FormData()
  formData.append('username', email)
  formData.append('password', password)
  const response = await api.post('/auth/login', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export const register = async (email: string, password: string) => {
  const response = await api.post('/auth/register', { email, password })
  return response.data
}

export const getMe = async () => {
  const response = await api.get('/auth/me')
  return response.data
}

// Profiles
export const getProfiles = async () => {
  const response = await api.get('/profiles')
  return response.data
}

export const createProfile = async (data: { platform: string; username: string; telegram_group_id?: number }) => {
  const response = await api.post('/profiles', data)
  return response.data
}

export const updateProfile = async (id: number, data: Partial<{ platform: string; username: string; active: boolean; telegram_group_id: number }>) => {
  const response = await api.put(`/profiles/${id}`, data)
  return response.data
}

export const deleteProfile = async (id: number) => {
  const response = await api.delete(`/profiles/${id}`)
  return response.data
}

export const toggleProfile = async (id: number) => {
  const response = await api.patch(`/profiles/${id}/toggle`)
  return response.data
}

export const testProfile = async (id: number) => {
  const response = await api.post(`/profiles/${id}/test`)
  return response.data
}

export const testProfileTelegram = async (id: number) => {
  const response = await api.post(`/profiles/${id}/test-telegram`)
  return response.data
}

// Keywords
export const getKeywords = async () => {
  const response = await api.get('/keywords')
  return response.data
}

export const createKeyword = async (data: { word: string; priority?: number }) => {
  const response = await api.post('/keywords', data)
  return response.data
}

export const updateKeyword = async (id: number, data: { word?: string; priority?: number }) => {
  const response = await api.put(`/keywords/${id}`, data)
  return response.data
}

export const deleteKeyword = async (id: number) => {
  const response = await api.delete(`/keywords/${id}`)
  return response.data
}

// Telegram
export const getTelegramGroups = async () => {
  const response = await api.get('/telegram/groups')
  return response.data
}

export const createTelegramGroup = async (data: { chat_id: string; name: string }) => {
  const response = await api.post('/telegram/groups', data)
  return response.data
}

export const updateTelegramGroup = async (id: number, data: { chat_id?: string; name?: string }) => {
  const response = await api.put(`/telegram/groups/${id}`, data)
  return response.data
}

export const deleteTelegramGroup = async (id: number) => {
  const response = await api.delete(`/telegram/groups/${id}`)
  return response.data
}

export const testTelegram = async (chat_id: string, message?: string) => {
  const response = await api.post('/telegram/test', { chat_id, message })
  return response.data
}

// Dashboard
export const getStats = async () => {
  const response = await api.get('/dashboard/stats')
  return response.data
}

export const getLogs = async (limit = 50) => {
  const response = await api.get(`/dashboard/logs?limit=${limit}`)
  return response.data
}

export interface PostsFilter {
  limit?: number
  offset?: number
  keyword_only?: boolean
  sent_only?: boolean
  profile_id?: number
  search?: string
}

export const getPosts = async (filters: PostsFilter = {}) => {
  const params = new URLSearchParams()
  if (filters.limit) params.append('limit', filters.limit.toString())
  if (filters.offset) params.append('offset', filters.offset.toString())
  if (filters.keyword_only) params.append('keyword_only', 'true')
  if (filters.sent_only) params.append('sent_only', 'true')
  if (filters.profile_id) params.append('profile_id', filters.profile_id.toString())
  if (filters.search) params.append('search', filters.search)

  const response = await api.get(`/dashboard/posts?${params.toString()}`)
  return response.data
}

// Settings
export interface AppSettings {
  id: number
  telegram_bot_token: string | null
  instagram_username: string | null
  instagram_password: string | null
  scrape_interval_hours: number
  scrape_delay_seconds: number
  use_proxies: boolean
  proxy_list: string | null
  groq_api_key: string | null
  enable_ai_summary: boolean
  updated_at: string | null
}

export const getAppSettings = async () => {
  const response = await api.get('/settings')
  return response.data as AppSettings
}

export const updateAppSettings = async (data: Partial<AppSettings>) => {
  const response = await api.put('/settings', data)
  return response.data as AppSettings
}

export const testTelegramConnection = async () => {
  const response = await api.post('/settings/test-telegram')
  return response.data
}

export default api
