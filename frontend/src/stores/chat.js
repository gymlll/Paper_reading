import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as chatApi from '../api/chat'

export const useChatStore = defineStore('chat', () => {
  const historyMap = ref({})
  const loading = ref(false)

  function getMessages(paperId) {
    return historyMap.value[paperId] || []
  }

  async function fetchHistory(paperId) {
    loading.value = true
    try {
      const res = await chatApi.getChatHistory(paperId)
      historyMap.value[paperId] = res.items || res.data || res
    } finally {
      loading.value = false
    }
  }

  async function sendMessage(paperId, question) {
    const messages = historyMap.value[paperId] || []
    messages.push({ role: 'user', content: question })
    historyMap.value[paperId] = [...messages]

    loading.value = true
    try {
      const res = await chatApi.sendMessage(paperId, { question })
      const answer = res.data || res
      messages.push({ role: 'assistant', content: answer.content || answer.answer })
      historyMap.value[paperId] = [...messages]
    } finally {
      loading.value = false
    }
  }

  async function clearHistory(paperId) {
    await chatApi.clearChat(paperId)
    historyMap.value[paperId] = []
  }

  return { historyMap, loading, getMessages, fetchHistory, sendMessage, clearHistory }
})
