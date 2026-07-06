import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getKeywords, createKeyword, updateKeyword, deleteKeyword } from '../services/api'
import { Plus, Trash2, Pencil, X } from 'lucide-react'

export default function Keywords() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingKeyword, setEditingKeyword] = useState<any>(null)
  const [formData, setFormData] = useState({ word: '', priority: 1 })

  const { data: keywords, isLoading } = useQuery({
    queryKey: ['keywords'],
    queryFn: getKeywords,
  })

  const createMutation = useMutation({
    mutationFn: createKeyword,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keywords'] })
      handleCancel()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => updateKeyword(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keywords'] })
      handleCancel()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteKeyword,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['keywords'] })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingKeyword) {
      updateMutation.mutate({ id: editingKeyword.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleEdit = (keyword: any) => {
    setEditingKeyword(keyword)
    setFormData({
      word: keyword.word,
      priority: keyword.priority,
    })
    setShowForm(true)
  }

  const handleCancel = () => {
    setEditingKeyword(null)
    setFormData({ word: '', priority: 1 })
    setShowForm(false)
  }

  const priorityLabels: Record<number, { label: string; color: string }> = {
    1: { label: 'Normal', color: 'bg-gray-100 text-gray-700' },
    2: { label: 'Importante', color: 'bg-yellow-100 text-yellow-700' },
    3: { label: 'Urgente', color: 'bg-red-100 text-red-700' },
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Palavras-chave</h1>
        <button
          onClick={() => {
            setEditingKeyword(null)
            setFormData({ word: '', priority: 1 })
            setShowForm(!showForm)
          }}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={20} />
          Adicionar Palavra
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium">
              {editingKeyword ? 'Editar Palavra-chave' : 'Nova Palavra-chave'}
            </h3>
            <button onClick={handleCancel} className="text-gray-500 hover:text-gray-700">
              <X size={20} />
            </button>
          </div>
          <form onSubmit={handleSubmit} className="flex gap-4">
            <input
              type="text"
              placeholder="Palavra-chave"
              value={formData.word}
              onChange={(e) => setFormData({ ...formData, word: e.target.value })}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
              required
            />

            <select
              value={formData.priority}
              onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
              className="px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value={1}>Normal</option>
              <option value={2}>Importante</option>
              <option value={3}>Urgente</option>
            </select>

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
        <p className="text-sm text-blue-700">
          Quando uma palavra-chave for encontrada em um post, o alerta será enviado com destaque.
          Palavras <strong>Urgentes</strong> geram alertas maiores no Telegram.
        </p>
      </div>

      {/* Keywords List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : keywords?.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          Nenhuma palavra-chave cadastrada. Adicione sua primeira!
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {keywords?.map((keyword: any) => {
            const priority = priorityLabels[keyword.priority] || priorityLabels[1]
            return (
              <div
                key={keyword.id}
                className="bg-white rounded-lg shadow p-4 flex items-center justify-between"
              >
                <div>
                  <p className="font-medium text-lg">{keyword.word}</p>
                  <span className={`text-xs px-2 py-1 rounded ${priority.color}`}>
                    {priority.label}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleEdit(keyword)}
                    className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg transition-colors"
                    title="Editar"
                  >
                    <Pencil size={18} />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm('Tem certeza que deseja excluir esta palavra-chave?')) {
                        deleteMutation.mutate(keyword.id)
                      }
                    }}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Excluir"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
