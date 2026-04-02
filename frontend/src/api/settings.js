import api from './index'

export function getProviders() {
  return api.get('/settings/providers')
}

export function addProvider(data) {
  return api.post('/settings/providers', data)
}

export function updateProvider(id, data) {
  return api.put(`/settings/providers/${id}`, data)
}

export function deleteProvider(id) {
  return api.delete(`/settings/providers/${id}`)
}

export function getModels() {
  return api.get('/settings/models')
}

export function testProvider(id) {
  return api.post(`/settings/test-provider/${id}`)
}
