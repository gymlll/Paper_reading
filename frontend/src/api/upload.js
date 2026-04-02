import api from './index'

export function uploadPdf(formData) {
  return api.post('/upload/pdf', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

export function getTaskStatus(taskId) {
  return api.get(`/upload/tasks/${taskId}`)
}

export function fullPipeline(paperId, data) {
  return api.post(`/upload/papers/${paperId}/full-pipeline`, data)
}
