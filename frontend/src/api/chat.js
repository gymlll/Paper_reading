import api from './index'

export function getChatHistory(paperId) {
  return api.get(`/chat/papers/${paperId}/messages`)
}

export function sendMessage(paperId, data) {
  return api.post(`/chat/papers/${paperId}/messages`, data)
}

export function sendMessageStream(paperId, data) {
  // Return fetch Response directly for streaming
  return fetch(`/api/v1/chat/papers/${paperId}/messages/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export function clearChat(paperId) {
  return api.delete(`/chat/papers/${paperId}/messages`)
}
