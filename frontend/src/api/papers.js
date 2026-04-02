import api from './index'

export function getPapers(params) {
  return api.get('/papers', { params })
}

export function getPaper(id) {
  return api.get(`/papers/${id}`)
}

export function getPaperPdf(id) {
  return api.get(`/papers/${id}/pdf`, { responseType: 'blob' })
}

export function updatePaper(id, data) {
  return api.put(`/papers/${id}`, data)
}

export function deletePaper(id) {
  return api.delete(`/papers/${id}`)
}
