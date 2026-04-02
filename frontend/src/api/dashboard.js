import api from './index'

export function getDashboard() {
  return api.get('/dashboard/stats')
}
