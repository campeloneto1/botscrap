import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getUsers, createUser, updateUser, deleteUser, User } from '../services/api'
import { Plus, Trash2, Pencil, X, Check, Ban, Shield, ShieldOff } from 'lucide-react'

export default function Users() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [search, setSearch] = useState('')
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    is_active: true,
    is_admin: false,
  })
  const [error, setError] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['users', search],
    queryFn: () => getUsers(0, 100, search || undefined),
  })

  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      handleCancel()
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Erro ao criar usuário')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => updateUser(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      handleCancel()
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Erro ao atualizar usuário')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || 'Erro ao deletar usuário')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (editingUser) {
      const updateData: any = {}
      if (formData.username !== editingUser.username) updateData.username = formData.username
      if (formData.email !== (editingUser.email || '')) updateData.email = formData.email || null
      if (formData.password) updateData.password = formData.password
      if (formData.is_active !== editingUser.is_active) updateData.is_active = formData.is_active
      if (formData.is_admin !== editingUser.is_admin) updateData.is_admin = formData.is_admin

      updateMutation.mutate({ id: editingUser.id, data: updateData })
    } else {
      createMutation.mutate({
        username: formData.username,
        password: formData.password,
        email: formData.email || undefined,
        is_active: formData.is_active,
        is_admin: formData.is_admin,
      })
    }
  }

  const handleEdit = (user: User) => {
    setEditingUser(user)
    setFormData({
      username: user.username,
      email: user.email || '',
      password: '',
      is_active: user.is_active,
      is_admin: user.is_admin,
    })
    setError('')
    setShowForm(true)
  }

  const handleCancel = () => {
    setEditingUser(null)
    setFormData({
      username: '',
      email: '',
      password: '',
      is_active: true,
      is_admin: false,
    })
    setError('')
    setShowForm(false)
  }

  const toggleActive = (user: User) => {
    updateMutation.mutate({
      id: user.id,
      data: { is_active: !user.is_active },
    })
  }

  const toggleAdmin = (user: User) => {
    updateMutation.mutate({
      id: user.id,
      data: { is_admin: !user.is_admin },
    })
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Usuários</h1>
        <button
          onClick={() => {
            setEditingUser(null)
            setFormData({
              username: '',
              email: '',
              password: '',
              is_active: true,
              is_admin: false,
            })
            setError('')
            setShowForm(!showForm)
          }}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={20} />
          Novo Usuário
        </button>
      </div>

      {/* Search */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="Buscar por username ou email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full md:w-96 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Form */}
      {showForm && (
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium">
              {editingUser ? 'Editar Usuário' : 'Novo Usuário'}
            </h3>
            <button onClick={handleCancel} className="text-gray-500 hover:text-gray-700">
              <X size={20} />
            </button>
          </div>

          {error && (
            <div className="bg-red-100 text-red-700 p-3 rounded mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Username *
                </label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                  placeholder="usuario123"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email (opcional)
                </label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="email@exemplo.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Senha {editingUser ? '(deixe vazio para manter)' : '*'}
                </label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required={!editingUser}
                  placeholder="******"
                />
              </div>

              <div className="flex items-center gap-6 pt-6">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="text-sm">Ativo</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_admin}
                    onChange={(e) => setFormData({ ...formData, is_admin: e.target.checked })}
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                  <span className="text-sm">Administrador</span>
                </label>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="bg-green-600 text-white px-6 py-2 rounded-md hover:bg-green-700 transition-colors disabled:opacity-50"
              >
                {createMutation.isPending || updateMutation.isPending ? 'Salvando...' : 'Salvar'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Users List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : data?.users?.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          Nenhum usuário encontrado.
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Usuário
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Admin
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Criado em
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {data?.users?.map((user: User) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="font-medium">{user.username}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                    {user.email || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <button
                      onClick={() => toggleActive(user)}
                      className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${
                        user.is_active
                          ? 'bg-green-100 text-green-700 hover:bg-green-200'
                          : 'bg-red-100 text-red-700 hover:bg-red-200'
                      }`}
                      title={user.is_active ? 'Clique para desativar' : 'Clique para ativar'}
                    >
                      {user.is_active ? <Check size={14} /> : <Ban size={14} />}
                      {user.is_active ? 'Ativo' : 'Inativo'}
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <button
                      onClick={() => toggleAdmin(user)}
                      className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${
                        user.is_admin
                          ? 'bg-purple-100 text-purple-700 hover:bg-purple-200'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                      title={user.is_admin ? 'Remover admin' : 'Tornar admin'}
                    >
                      {user.is_admin ? <Shield size={14} /> : <ShieldOff size={14} />}
                      {user.is_admin ? 'Admin' : 'Usuário'}
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-500 text-sm">
                    {new Date(user.created_at).toLocaleDateString('pt-BR')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleEdit(user)}
                        className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg transition-colors"
                        title="Editar"
                      >
                        <Pencil size={18} />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`Tem certeza que deseja excluir o usuário "${user.username}"?`)) {
                            deleteMutation.mutate(user.id)
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
              ))}
            </tbody>
          </table>

          {data && (
            <div className="px-6 py-3 bg-gray-50 text-sm text-gray-500">
              Total: {data.total} usuário(s)
            </div>
          )}
        </div>
      )}
    </div>
  )
}
