import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as settingsApi from '../api/settings'

export const useSettingsStore = defineStore('settings', () => {
  const providers = ref([])
  const models = ref([])
  const theme = ref(localStorage.getItem('theme') || 'light')
  const loading = ref(false)

  async function fetchProviders() {
    loading.value = true
    try {
      const res = await settingsApi.getProviders()
      providers.value = res.items || res.data || res
    } finally {
      loading.value = false
    }
  }

  async function fetchModels() {
    try {
      const res = await settingsApi.getModels()
      models.value = res.items || res.data || res
    } catch {
      models.value = []
    }
  }

  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    localStorage.setItem('theme', theme.value)
    document.body.setAttribute('arco-theme', theme.value)
  }

  return { providers, models, theme, loading, fetchProviders, fetchModels, toggleTheme }
})
