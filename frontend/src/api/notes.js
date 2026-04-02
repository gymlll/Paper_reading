import api from './index'

export function getNote(paperId) {
  return api.get(`/notes/papers/${paperId}/note`)
}

export function createNote(paperId, data) {
  return api.post(`/notes/papers/${paperId}/note`, data)
}

export function updateNote(noteId, data) {
  return api.put(`/notes/${noteId}`, data)
}

export function generateNote(paperId, providerId, modelId) {
  return api.post(`/notes/papers/${paperId}/generate-note`, { provider_id: providerId, model_id: modelId })
}
