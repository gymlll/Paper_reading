import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as paperApi from '../api/papers'

export const usePaperStore = defineStore('paper', () => {
  const papers = ref([])
  const currentPaper = ref(null)
  const loading = ref(false)
  const total = ref(0)

  async function fetchPapers(params = {}) {
    loading.value = true
    try {
      const res = await paperApi.getPapers(params)
      papers.value = res.items || res.data || res
      total.value = res.total || papers.value.length
    } finally {
      loading.value = false
    }
  }

  async function fetchPaper(id) {
    loading.value = true
    try {
      const res = await paperApi.getPaper(id)
      currentPaper.value = res.item || res.data || res
    } finally {
      loading.value = false
    }
  }

  async function updatePaper(id, data) {
    const res = await paperApi.updatePaper(id, data)
    if (currentPaper.value?.id === id) {
      currentPaper.value = res.item || res.data || res
    }
  }

  async function deletePaper(id) {
    await paperApi.deletePaper(id)
    papers.value = papers.value.filter((p) => p.id !== id)
    if (currentPaper.value?.id === id) {
      currentPaper.value = null
    }
  }

  return { papers, currentPaper, loading, total, fetchPapers, fetchPaper, updatePaper, deletePaper }
})
