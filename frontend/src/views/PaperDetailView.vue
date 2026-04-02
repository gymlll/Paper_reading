<template>
  <div style="height: calc(100vh - var(--header-height, 56px)); display: flex; overflow: hidden;">
    <!-- Left: PDF / Markdown viewer -->
    <div style="flex: 1; display: flex; flex-direction: column; min-width: 0; border-right: 1px solid var(--color-border);">
      <div style="padding: 12px 16px; border-bottom: 1px solid var(--color-border); display: flex; align-items: center; gap: 12px; flex-shrink: 0;">
        <h3 style="margin: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 15px;">
          {{ paper?.title || paper?.filename || 'Loading...' }}
        </h3>
        <a-radio-group v-model="leftView" type="button" size="small">
          <a-radio value="pdf">PDF</a-radio>
          <a-radio value="md">Markdown</a-radio>
        </a-radio-group>
      </div>

      <div style="flex: 1; overflow: auto;">
        <div v-if="leftView === 'pdf'">
          <div v-if="pdfLoading" style="display: flex; justify-content: center; padding: 60px;">
            <a-spin :size="32" tip="Loading PDF..." />
          </div>
          <div v-else-if="pdfSource" style="width: 100%;">
            <VuePdfEmbed :source="pdfSource" @loading="onPdfLoading" @rendered="onPdfRendered" />
          </div>
          <a-empty v-else style="margin-top: 60px;" description="PDF not available" />
        </div>
        <div v-else class="academic-md" style="padding: 24px 32px;">
          <div v-if="paper?.md_content" v-html="renderedMd"></div>
          <a-empty v-else style="margin-top: 60px;" description="No parsed content" />
        </div>
      </div>
    </div>

    <!-- Right: Notes + Chat -->
    <div style="width: 480px; flex-shrink: 0; display: flex; flex-direction: column; overflow: hidden;">
      <a-tabs v-model:active-key="rightTab" style="height: 100%; display: flex; flex-direction: column;">
        <a-tab-pane key="note" title="Notes" style="height: 100%;">
          <div style="height: calc(100vh - var(--header-height, 56px) - 46px); overflow-y: auto; padding: 16px;">
            <div v-if="note">
              <div v-if="!editing" class="academic-md" v-html="renderedNote"></div>
              <div v-else>
                <a-textarea v-model="editContent" :auto-size="{ minRows: 20, maxRows: 40 }" />
                <div style="margin-top: 12px; display: flex; gap: 8px;">
                  <a-button type="primary" @click="saveNote">Save</a-button>
                  <a-button @click="editing = false">Cancel</a-button>
                </div>
              </div>
              <a-divider />
              <a-space>
                <a-button v-if="!editing" type="outline" size="small" @click="startEdit">Edit</a-button>
                <a-button type="primary" size="small" @click="doGenerateNote" :loading="generating">
                  AI Generate
                </a-button>
              </a-space>
            </div>
            <div v-else style="text-align: center; padding: 60px 20px;">
              <a-empty description="No notes yet">
                <a-button type="primary" @click="doGenerateNote" :loading="generating">AI Generate Note</a-button>
              </a-empty>
            </div>
          </div>
        </a-tab-pane>

        <a-tab-pane key="chat" title="Chat" style="height: 100%;">
          <!-- Full-height chat: messages scroll, input fixed at bottom -->
          <div style="height: calc(100vh - var(--header-height, 56px) - 46px); display: flex; flex-direction: column;">
            <!-- Messages area -->
            <div ref="chatContainer" style="flex: 1; overflow-y: auto; padding: 16px;">
              <div v-if="messages.length === 0" style="text-align: center; padding: 30px 10px; color: var(--color-text-3);">
                <p style="font-size: 15px; margin-bottom: 16px;">Hi! I'm your paper reading assistant.</p>
                <p style="margin-bottom: 12px; font-size: 13px;">Quick questions:</p>
                <a-space wrap>
                  <a-button size="small" type="outline" @click="askPreset('What are the main contributions?')">Main Contributions</a-button>
                  <a-button size="small" type="outline" @click="askPreset('What are the limitations?')">Limitations</a-button>
                  <a-button size="small" type="outline" @click="askPreset('What is the core method?')">Core Method</a-button>
                  <a-button size="small" type="outline" @click="askPreset('What inspirations for my research?')">Inspirations</a-button>
                </a-space>
              </div>

              <div v-for="msg in messages" :key="msg.id" style="margin-bottom: 16px; display: flex; gap: 10px;" :style="{ flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }">
                <div style="width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; flex-shrink: 0; font-weight: 600;"
                  :style="{ background: msg.role === 'assistant' ? 'rgb(var(--arcoblue-6))' : 'rgb(var(--arcogreen-6))', color: '#fff' }">
                  {{ msg.role === 'assistant' ? 'AI' : 'U' }}
                </div>
                <div style="max-width: 80%; padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.7;"
                  :style="{ background: msg.role === 'user' ? 'rgb(var(--arcoblue-6))' : 'var(--color-fill-2)', color: msg.role === 'user' ? '#fff' : 'inherit' }"
                  v-html="renderMd(msg.content)"></div>
              </div>

              <div v-if="chatLoading" style="margin-bottom: 16px; display: flex; gap: 10px;">
                <div style="width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; background: rgb(var(--arcoblue-6)); color: #fff; flex-shrink: 0; font-weight: 600;">AI</div>
                <div style="padding: 12px 16px; border-radius: 12px; background: var(--color-fill-2);">
                  <a-spin :size="16" />
                </div>
              </div>
            </div>

            <!-- Fixed input at bottom -->
            <div style="padding: 12px 16px; border-top: 1px solid var(--color-border); display: flex; gap: 8px; flex-shrink: 0;">
              <a-input
                v-model="chatInput"
                placeholder="Ask about this paper... (Enter to send)"
                @press-enter="sendChat"
                :disabled="chatLoading"
                style="flex: 1;"
              />
              <a-button type="primary" @click="sendChat" :loading="chatLoading">Send</a-button>
            </div>
          </div>
        </a-tab-pane>
      </a-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import MarkdownIt from 'markdown-it'
import mk from '@traptitech/markdown-it-katex'
import VuePdfEmbed from 'vue-pdf-embed'
import { getPaper } from '../api/papers'
import { getNote, updateNote, generateNote } from '../api/notes'
import { getChatHistory, sendMessageStream } from '../api/chat'

const md = new MarkdownIt({ html: true, linkify: true })
md.use(mk)


// (md instance created above with KaTeX support)

const route = useRoute()
const paper = ref(null)
const note = ref(null)
const leftView = ref('pdf')
const rightTab = ref('note')
const pdfSource = ref('')
const pdfLoading = ref(true)
const editing = ref(false)
const editContent = ref('')
const generating = ref(false)
const messages = ref([])
const chatInput = ref('')
const chatLoading = ref(false)
const chatContainer = ref(null)

const renderedMd = computed(() => {
  if (!paper.value?.md_content) return ''
  return md.render(paper.value.md_content)
})

const renderedNote = computed(() => {
  if (!note.value?.content) return ''
  return md.render(note.value.content)
})

function renderMd(content) {
  return md.render(content || '')
}

function onPdfLoading(loading) {
  pdfLoading.value = loading
}

function onPdfRendered() {
  pdfLoading.value = false
}

async function loadData() {
  const id = route.params.id
  try {
    const [paperData, noteData, chatData] = await Promise.all([
      getPaper(id),
      getNote(id).catch(() => null),
      getChatHistory(id).catch(() => []),
    ])
    paper.value = paperData
    note.value = noteData
    messages.value = chatData || []

    if (paperData.id) {
      // Fetch PDF as blob to avoid proxy/binary issues with vue-pdf-embed
      try {
        const pdfResp = await fetch(`/api/v1/papers/${paperData.id}/pdf`)
        const blob = await pdfResp.blob()
        pdfSource.value = URL.createObjectURL(blob)
      } catch (e) {
        console.error('Failed to load PDF:', e)
      } finally {
        pdfLoading.value = false
      }
    }
  } catch (e) {
    console.error('Failed to load paper:', e)
  }
}

function startEdit() {
  editContent.value = note.value?.content || ''
  editing.value = true
}

async function saveNote() {
  if (!note.value) return
  try {
    const result = await updateNote(note.value.id, { content: editContent.value })
    note.value = result
    editing.value = false
  } catch (e) {
    console.error('Failed to save note:', e)
  }
}

async function doGenerateNote() {
  generating.value = true
  try {
    await generateNote(paper.value.id)
    for (let i = 0; i < 60; i++) {
      await new Promise(r => setTimeout(r, 3000))
      try {
        const n = await getNote(paper.value.id)
        if (n) { note.value = n; break }
      } catch {}
    }
  } catch (e) {
    console.error('Failed to generate note:', e)
  } finally {
    generating.value = false
  }
}

async function sendChat() {
  const question = chatInput.value.trim()
  if (!question || chatLoading.value) return

  chatInput.value = ''
  chatLoading.value = true

  messages.value.push({ id: Date.now(), role: 'user', content: question })
  await nextTick()
  scrollChat()

  // Add empty assistant message for streaming
  const assistantId = Date.now() + 1
  const assistantMsg = { id: assistantId, role: 'assistant', content: '' }
  messages.value.push(assistantMsg)
  await nextTick()

  try {
    const resp = await sendMessageStream(paper.value.id, { question })
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`)
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value, { stream: true })
      assistantMsg.content += chunk

      // Update reactive reference
      messages.value = [...messages.value]
      await nextTick()
      scrollChat()
    }
  } catch (e) {
    console.error('Chat failed:', e)
    // Remove empty assistant message on error
    const idx = messages.value.findIndex(m => m.id === assistantId)
    if (idx >= 0 && !messages.value[idx].content) {
      messages.value.splice(idx, 1)
    }
  } finally {
    chatLoading.value = false
    await nextTick()
    scrollChat()
  }
}

function askPreset(question) {
  chatInput.value = question
  sendChat()
}

function scrollChat() {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

onMounted(loadData)

onUnmounted(() => {
  if (pdfSource.value && pdfSource.value.startsWith('blob:')) {
    URL.revokeObjectURL(pdfSource.value)
  }
})
</script>
