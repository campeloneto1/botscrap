import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getTelegramGroups, createTelegramGroup, updateTelegramGroup, deleteTelegramGroup, testTelegram } from '../services/api'
import { Plus, Trash2, Send, CheckCircle, XCircle, Pencil, X } from 'lucide-react'

export default function TelegramGroups() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingGroup, setEditingGroup] = useState<any>(null)
  const [formData, setFormData] = useState({ chat_id: '', name: '' })
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)

  const { data: groups, isLoading } = useQuery({
    queryKey: ['telegram-groups'],
    queryFn: getTelegramGroups,
  })

  const createMutation = useMutation({
    mutationFn: createTelegramGroup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['telegram-groups'] })
      setShowForm(false)
      setFormData({ chat_id: '', name: '' })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { chat_id?: string; name?: string } }) =>
      updateTelegramGroup(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['telegram-groups'] })
      setEditingGroup(null)
      setFormData({ chat_id: '', name: '' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteTelegramGroup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['telegram-groups'] })
    },
  })

  const testMutation = useMutation({
    mutationFn: (chatId: string) => testTelegram(chatId),
    onSuccess: (data) => {
      setTestResult({
        success: data.success,
        message: data.success ? 'Mensagem enviada com sucesso!' : data.error,
      })
      setTimeout(() => setTestResult(null), 5000)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingGroup) {
      updateMutation.mutate({ id: editingGroup.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleEdit = (group: any) => {
    setEditingGroup(group)
    setFormData({ chat_id: group.chat_id, name: group.name })
    setShowForm(true)
  }

  const handleCancel = () => {
    setEditingGroup(null)
    setFormData({ chat_id: '', name: '' })
    setShowForm(false)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Grupos do Telegram</h1>
        <button
          onClick={() => {
            setEditingGroup(null)
            setFormData({ chat_id: '', name: '' })
            setShowForm(!showForm)
          }}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={20} />
          Adicionar Grupo
        </button>
      </div>

      {/* Test Result */}
      {testResult && (
        <div
          className={`p-4 rounded-lg mb-6 flex items-center gap-3 ${
            testResult.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}
        >
          {testResult.success ? <CheckCircle size={20} /> : <XCircle size={20} />}
          {testResult.message}
        </div>
      )}

      {/* Form */}
      {showForm && (
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium">
              {editingGroup ? 'Editar Grupo' : 'Novo Grupo'}
            </h3>
            <button onClick={handleCancel} className="text-gray-500 hover:text-gray-700">
              <X size={20} />
            </button>
          </div>
          <form onSubmit={handleSubmit} className="flex gap-4">
            <input
              type="text"
              placeholder="Nome do grupo"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
              required
            />

            <input
              type="text"
              placeholder="Chat ID (ex: -100123456789)"
              value={formData.chat_id}
              onChange={(e) => setFormData({ ...formData, chat_id: e.target.value })}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
              required
            />

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

      {/* Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <p className="text-sm text-blue-700 mb-2">
          <strong>Como obter o Chat ID do grupo:</strong>
        </p>
        <ol className="text-sm text-blue-700 list-decimal list-inside space-y-1">
          <li>Adicione o bot @userinfobot ao seu grupo</li>
          <li>O bot vai enviar o Chat ID do grupo</li>
          <li>O ID geralmente começa com -100</li>
          <li>Remova o @userinfobot depois</li>
        </ol>
      </div>

      {/* Groups List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : groups?.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          Nenhum grupo cadastrado. Adicione seu primeiro grupo!
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Nome</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Chat ID</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Status</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {groups?.map((group: any) => (
                <tr key={group.id}>
                  <td className="px-4 py-3 font-medium">{group.name}</td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-sm">{group.chat_id}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-1 text-xs rounded-full ${
                        group.active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {group.active ? 'Ativo' : 'Inativo'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => testMutation.mutate(group.chat_id)}
                        disabled={testMutation.isPending}
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Enviar mensagem de teste"
                      >
                        <Send size={18} />
                      </button>
                      <button
                        onClick={() => handleEdit(group)}
                        className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg transition-colors"
                        title="Editar"
                      >
                        <Pencil size={18} />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm('Tem certeza que deseja excluir este grupo?')) {
                            deleteMutation.mutate(group.id)
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
        </div>
      )}
    </div>
  )
}
