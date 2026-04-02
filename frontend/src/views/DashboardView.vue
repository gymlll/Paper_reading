<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  IconFile,
  IconCalendar,
  IconRobot,
  IconClockCircle,
  IconUpload,
  IconArrowRight,
} from '@arco-design/web-vue/es/icon'
import { getDashboard } from '../api/dashboard'

const router = useRouter()

const loading = ref(false)
const stats = ref({
  total_papers: 0,
  this_month: 0,
  ai_notes: 0,
  pending: 0,
})
const recentPapers = ref([])

// 统计卡片配置
const statCards = [
  { key: 'total_papers', label: '论文总数', icon: IconFile, color: '#165DFF' },
  { key: 'this_month', label: '本月新增', icon: IconCalendar, color: '#0FC6C2' },
  { key: 'ai_notes', label: 'AI 笔记', icon: IconRobot, color: '#722ED1' },
  { key: 'pending', label: '待处理', icon: IconClockCircle, color: '#FF7D00' },
]

// 论文状态映射
const statusMap = {
  uploaded: { text: '已上传', color: 'arcoblue' },
  parsing: { text: '解析中', color: 'orange' },
  parsed: { text: '已解析', color: 'green' },
  noted: { text: '已笔记', color: 'purple' },
  error: { text: '错误', color: 'red' },
}

// 表格列定义
const tableColumns = [
  { title: '标题', dataIndex: 'title', ellipsis: true, width: 300 },
  { title: '状态', dataIndex: 'status', width: 100, slotName: 'status' },
  { title: '是否有笔记', dataIndex: 'has_note', width: 110, slotName: 'hasNote' },
  { title: '日期', dataIndex: 'created_at', width: 120, slotName: 'date' },
  { title: '操作', width: 80, slotName: 'actions' },
]

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return dateStr.slice(0, 10)
}

function getStatusInfo(status) {
  return statusMap[status] || { text: status, color: 'gray' }
}

function goToPaper(row) {
  router.push(`/papers/${row.id}`)
}

async function fetchStats() {
  loading.value = true
  try {
    const data = await getDashboard()
    const s = data.stats || data
    stats.value = {
      total_papers: s.total_papers ?? 0,
      this_month: s.papers_this_month ?? 0,
      ai_notes: s.ai_notes_count ?? 0,
      pending: s.pending_papers ?? 0,
    }
    recentPapers.value = data.recent_papers || []
  } catch (err) {
    console.error('获取仪表盘数据失败:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<template>
  <div class="dashboard-view">
    <!-- 统计卡片行 -->
    <a-row :gutter="16" class="stat-row">
      <a-col
        v-for="card in statCards"
        :key="card.key"
        :span="6"
      >
        <a-card class="stat-card" :bordered="false" hoverable>
          <div class="stat-card-inner">
            <div
              class="stat-icon"
              :style="{ background: card.color + '15', color: card.color }"
            >
              <component :is="card.icon" :size="24" />
            </div>
            <a-statistic
              :title="card.label"
              :value="stats[card.key]"
              :animation="true"
              :value-from="0"
              class="stat-value"
            />
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 快速操作区 -->
    <div class="section-header">
      <a-typography-title :heading="5" style="margin: 0">快速操作</a-typography-title>
    </div>
    <div class="quick-actions">
      <a-button type="primary" size="large" @click="router.push('/upload')">
        <template #icon><IconUpload /></template>
        上传论文
      </a-button>
      <a-button size="large" @click="router.push('/papers')">
        <template #icon><IconArrowRight /></template>
        浏览论文库
      </a-button>
    </div>

    <!-- 最近论文表格 -->
    <div class="section-header">
      <a-typography-title :heading="5" style="margin: 0">最近论文</a-typography-title>
    </div>
    <a-card :bordered="false">
      <a-table
        :columns="tableColumns"
        :data="recentPapers"
        :loading="loading"
        :pagination="false"
        row-key="id"
        stripe
      >
        <template #status="{ record }">
          <a-tag
            :color="getStatusInfo(record.status).color"
            size="small"
          >
            {{ getStatusInfo(record.status).text }}
          </a-tag>
        </template>

        <template #hasNote="{ record }">
          <a-tag v-if="record.has_note" color="green" size="small">有笔记</a-tag>
          <a-tag v-else color="gray" size="small">无笔记</a-tag>
        </template>

        <template #date="{ record }">
          {{ formatDate(record.created_at) }}
        </template>

        <template #actions="{ record }">
          <a-button type="text" size="small" @click="goToPaper(record)">
            查看
          </a-button>
        </template>
      </a-table>

      <a-empty
        v-if="!loading && recentPapers.length === 0"
        description="暂无论文，点击上方按钮上传"
      />
    </a-card>
  </div>
</template>

<style scoped>
.dashboard-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stat-row {
  margin-bottom: 4px;
}

.stat-card {
  border-radius: 8px;
}

.stat-card-inner {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-value {
  flex: 1;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}

.quick-actions {
  display: flex;
  gap: 12px;
}
</style>
