<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  IconUpload,
  IconFilePdf,
  IconEye,
} from '@arco-design/web-vue/es/icon'
import { uploadPdf, getTaskStatus } from '../api/upload'

const router = useRouter()

// ---------- 状态管理 ----------
const currentStep = ref(0) // 0=上传, 1=解析中, 2=完成, 3=生成笔记
const file = ref(null)
const parseProgress = ref(0)
const taskId = ref(null)
const paperId = ref(null)
const errorMessage = ref('')
const polling = ref(false)
let pollTimer = null

// 步骤配置
const steps = [
  { title: '上传文件' },
  { title: '解析论文' },
  { title: '解析完成' },
  { title: '生成笔记' },
]

// 每个步骤的状态：finish / process / wait
function getStepStatus(index) {
  if (index < currentStep.value) return 'finish'
  if (index === currentStep.value) return 'process'
  return 'wait'
}

// ---------- 上传处理 ----------
async function handleUpload(fileList) {
  const uploadFile = fileList[fileList.length - 1]
  if (!uploadFile) return

  const rawFile = uploadFile.file
  if (!rawFile.name.toLowerCase().endsWith('.pdf')) {
    errorMessage.value = '仅支持 PDF 文件格式'
    return
  }

  file.value = rawFile
  currentStep.value = 0
  errorMessage.value = ''
  parseProgress.value = 0

  await startUpload(rawFile)
}

async function startUpload(rawFile) {
  try {
    currentStep.value = 0
    const formData = new FormData()
    formData.append('file', rawFile)

    const result = await uploadPdf(formData)

    taskId.value = result.task_id
    paperId.value = result.paper_id

    // 进入解析阶段
    currentStep.value = 1
    startPolling()
  } catch (err) {
    errorMessage.value = err?.response?.data?.detail || err.message || '上传失败，请重试'
    currentStep.value = 0
  }
}

// ---------- 轮询解析状态（每 3 秒） ----------
function startPolling() {
  polling.value = true
  pollTimer = setInterval(async () => {
    try {
      const status = await getTaskStatus(taskId.value)

      // 后端完成时 status='done'，进度=100
      if (status.status === 'done' || status.status === 'completed') {
        parseProgress.value = 100
        polling.value = false
        clearInterval(pollTimer)
        pollTimer = null

        setTimeout(() => {
          currentStep.value = 2
        }, 500)
      } else if (status.status === 'failed') {
        polling.value = false
        clearInterval(pollTimer)
        pollTimer = null
        errorMessage.value = status.error || status.message || '论文解析失败，请重试'
      } else {
        // 更新进度
        parseProgress.value = status.progress ?? Math.min(parseProgress.value + 10, 90)
      }
    } catch (err) {
      console.error('轮询任务状态失败:', err)
    }
  }, 3000)
}

// ---------- 操作 ----------
function handleRetry() {
  errorMessage.value = ''
  currentStep.value = 0
  parseProgress.value = 0
  file.value = null
  taskId.value = null
  paperId.value = null
}

function goToPaper() {
  if (paperId.value) {
    router.push(`/papers/${paperId.value}`)
  }
}

function goToLibrary() {
  router.push('/papers')
}

// 清理定时器
onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
  }
})
</script>

<template>
  <div class="upload-view">
    <!-- 步骤条 -->
    <a-card :bordered="false" class="steps-card">
      <a-steps :current="currentStep" line-less>
        <a-step
          v-for="(step, index) in steps"
          :key="index"
          :title="step.title"
          :status="getStepStatus(index)"
        />
      </a-steps>
    </a-card>

    <!-- 步骤 0：上传区域 -->
    <div v-if="currentStep === 0" class="upload-section">
      <a-upload
        draggable
        accept=".pdf"
        :auto-upload="false"
        :limit="1"
        :show-file-list="false"
        @change="handleUpload"
      >
        <template #upload-button>
          <div class="upload-zone">
            <div class="upload-zone-content">
              <IconUpload :size="48" style="color: rgb(var(--arcoblue-6)); margin-bottom: 16px" />
              <div class="upload-zone-title">点击或拖拽文件到此处上传</div>
              <div class="upload-zone-hint">仅支持 PDF 格式的学术论文</div>
            </div>
          </div>
        </template>
      </a-upload>

      <a-alert
        v-if="errorMessage"
        type="error"
        :closable="true"
        style="margin-top: 16px"
      >
        {{ errorMessage }}
      </a-alert>
    </div>

    <!-- 步骤 1：解析中 -->
    <div v-if="currentStep === 1" class="parsing-section">
      <a-card :bordered="false" class="status-card">
        <a-result title="论文解析中" sub-title="正在提取论文内容，请稍候...">
          <template #icon>
            <IconFilePdf :size="48" style="color: rgb(var(--arcoblue-6))" />
          </template>
        </a-result>

        <div class="progress-section">
          <a-progress
            :percent="parseProgress / 100"
            :show-text="true"
            :status="errorMessage ? 'danger' : 'normal'"
            animation
          />
          <a-typography-text v-if="polling" type="secondary" style="margin-top: 8px; display: block">
            解析进度将持续更新...
          </a-typography-text>
        </div>

        <a-alert
          v-if="errorMessage"
          type="error"
          style="margin-top: 16px"
        >
          {{ errorMessage }}
          <template #action>
            <a-button size="small" type="primary" @click="handleRetry">
              重新上传
            </a-button>
          </template>
        </a-alert>
      </a-card>
    </div>

    <!-- 步骤 2：解析完成 -->
    <div v-if="currentStep === 2" class="complete-section">
      <a-card :bordered="false" class="status-card">
        <a-result
          status="success"
          title="解析完成"
          sub-title="论文已成功解析，您可以查看详情或继续操作"
        >
          <template #extra>
            <a-space>
              <a-button type="primary" size="large" @click="goToPaper">
                <template #icon><IconEye /></template>
                查看论文
              </a-button>
              <a-button size="large" @click="handleRetry">
                <template #icon><IconUpload /></template>
                继续上传
              </a-button>
            </a-space>
          </template>
        </a-result>
      </a-card>
    </div>

    <!-- 步骤 3：笔记生成完成 -->
    <div v-if="currentStep === 3" class="note-section">
      <a-card :bordered="false" class="status-card">
        <a-result
          status="success"
          title="全部完成"
          sub-title="论文解析和笔记生成均已完成"
        >
          <template #extra>
            <a-space>
              <a-button type="primary" size="large" @click="goToPaper">
                <template #icon><IconEye /></template>
                查看论文和笔记
              </a-button>
              <a-button size="large" @click="goToLibrary">
                <template #icon><IconFilePdf /></template>
                返回论文库
              </a-button>
              <a-button size="large" @click="handleRetry">
                <template #icon><IconUpload /></template>
                继续上传
              </a-button>
            </a-space>
          </template>
        </a-result>
      </a-card>
    </div>

    <!-- 上传须知 -->
    <a-card v-if="currentStep === 0" :bordered="false" class="tips-card">
      <a-typography-title :heading="6">上传须知</a-typography-title>
      <a-typography-ol>
        <a-typography-li>仅支持 PDF 格式的学术论文文件</a-typography-li>
        <a-typography-li>上传后将自动开始解析论文内容</a-typography-li>
        <a-typography-li>解析完成后可使用 AI 自动生成阅读笔记</a-typography-li>
        <a-typography-li>单文件大小建议不超过 50MB</a-typography-li>
      </a-typography-ol>
    </a-card>
  </div>
</template>

<style scoped>
.upload-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.steps-card {
  border-radius: 8px;
}

.upload-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.upload-zone {
  border: 2px dashed var(--color-border-2);
  border-radius: 12px;
  padding: 60px 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--color-fill-1);
}

.upload-zone:hover {
  border-color: rgb(var(--arcoblue-6));
  background: rgb(var(--arcoblue-1));
}

.upload-zone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.upload-zone-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--color-text-1);
  margin-bottom: 8px;
}

.upload-zone-hint {
  font-size: 14px;
  color: var(--color-text-3);
}

.progress-section {
  padding: 0 16px;
}

.status-card {
  border-radius: 8px;
  text-align: center;
}

.tips-card {
  border-radius: 8px;
  max-width: 500px;
}
</style>
