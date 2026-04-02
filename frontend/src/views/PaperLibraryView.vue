<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  IconSearch,
  IconRefresh,
  IconDelete,
  IconEye,
  IconFile,
  IconCheckCircle,
} from '@arco-design/web-vue/es/icon'
import { getPapers, deletePaper } from '../api/papers'

const router = useRouter()

// ---------- 筛选条件 ----------
const filters = reactive({
  search: '',
  status: '',
  year: '',
  sort: 'created_at_desc',
})

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '已上传', value: 'uploaded' },
  { label: '解析中', value: 'parsing' },
  { label: '已解析', value: 'parsed' },
  { label: '已笔记', value: 'noted' },
  { label: '错误', value: 'error' },
]

const sortOptions = [
  { label: '最新上传', value: 'created_at_desc' },
  { label: '最早上传', value: 'created_at_asc' },
  { label: '按标题 A-Z', value: 'title_asc' },
  { label: '按年份新到旧', value: 'year_desc' },
  { label: '按年份旧到新', value: 'year_asc' },
]

// 动态生成近 10 年
const currentYear = new Date().getFullYear()
const yearOptions = [
  { label: '全部年份', value: '' },
  ...Array.from({ length: 10 }, (_, i) => ({
    label: String(currentYear - i),
    value: String(currentYear - i),
  })),
]

// ---------- 表格数据 ----------
const loading = ref(false)
const tableData = ref([])
const pagination = reactive({
  current: 1,
  pageSize: 15,
  total: 0,
})

// 状态颜色和文本映射
const statusColorMap = {
  uploaded: 'arcoblue',
  parsing: 'orange',
  parsed: 'green',
  noted: 'purple',
  error: 'red',
}

const statusTextMap = {
  uploaded: '已上传',
  parsing: '解析中',
  parsed: '已解析',
  noted: '已笔记',
  error: '错误',
}

// 表格列定义
const tableColumns = [
  { title: '#', slotName: 'index', width: 50 },
  { title: '标题', dataIndex: 'title', ellipsis: true, slotName: 'title' },
  { title: '作者', dataIndex: 'authors', ellipsis: true, width: 180, slotName: 'authors' },
  { title: '年份', dataIndex: 'year', width: 70, align: 'center' },
  { title: '来源', dataIndex: 'venue', ellipsis: true, width: 140 },
  { title: '状态', dataIndex: 'status', width: 90, slotName: 'status' },
  { title: '笔记', dataIndex: 'has_note', width: 70, align: 'center', slotName: 'noteStatus' },
  { title: '操作', width: 100, align: 'center', slotName: 'actions' },
]

// ---------- 数据获取 ----------
async function fetchPapers() {
  loading.value = true
  try {
    const params = {
      page: pagination.current,
      page_size: pagination.pageSize,
    }
    if (filters.search) params.search = filters.search
    if (filters.status) params.status = filters.status
    if (filters.year) params.year = filters.year
    if (filters.sort) params.sort = filters.sort

    const data = await getPapers(params)
    tableData.value = data.items || []
    pagination.total = data.total || 0
  } catch (err) {
    console.error('获取论文列表失败:', err)
    tableData.value = []
  } finally {
    loading.value = false
  }
}

function handlePageChange(page) {
  pagination.current = page
  fetchPapers()
}

function handlePageSizeChange(pageSize) {
  pagination.pageSize = pageSize
  pagination.current = 1
  fetchPapers()
}

function handleSearch() {
  pagination.current = 1
  fetchPapers()
}

function handleReset() {
  filters.search = ''
  filters.status = ''
  filters.year = ''
  filters.sort = 'created_at_desc'
  pagination.current = 1
  fetchPapers()
}

function goDetail(row) {
  router.push(`/papers/${row.id}`)
}

async function confirmDelete(record) {
  try {
    await deletePaper(record.id)
    await fetchPapers()
  } catch (err) {
    console.error('删除失败:', err)
  }
}

onMounted(() => {
  fetchPapers()
})

// 下拉筛选变化时自动刷新
watch(
  [() => filters.status, () => filters.year, () => filters.sort],
  () => {
    pagination.current = 1
    fetchPapers()
  }
)
</script>

<template>
  <div class="paper-library-view">
    <!-- 筛选栏 -->
    <a-card :bordered="false" class="filter-card">
      <a-row :gutter="16" align="center">
        <a-col :flex="1">
          <a-input-search
            v-model="filters.search"
            placeholder="搜索论文标题、作者..."
            search-button
            allow-clear
            @search="handleSearch"
            @clear="handleSearch"
          />
        </a-col>
        <a-col :span="4">
          <a-select
            v-model="filters.status"
            placeholder="状态筛选"
            :options="statusOptions"
            allow-clear
          />
        </a-col>
        <a-col :span="3">
          <a-select
            v-model="filters.year"
            placeholder="年份"
            :options="yearOptions"
            allow-clear
          />
        </a-col>
        <a-col :span="4">
          <a-select
            v-model="filters.sort"
            placeholder="排序方式"
            :options="sortOptions"
          />
        </a-col>
        <a-col :span="auto">
          <a-button @click="handleReset">
            <template #icon><IconRefresh /></template>
            重置
          </a-button>
        </a-col>
      </a-row>
    </a-card>

    <!-- 论文表格 -->
    <a-card :bordered="false">
      <a-table
        :columns="tableColumns"
        :data="tableData"
        :loading="loading"
        row-key="id"
        stripe
        :pagination="{
          current: pagination.current,
          pageSize: pagination.pageSize,
          total: pagination.total,
          showTotal: true,
          showPageSize: true,
        }"
        @page-change="handlePageChange"
        @page-size-change="handlePageSizeChange"
      >
        <template #index="{ rowIndex }">
          {{ (pagination.current - 1) * pagination.pageSize + rowIndex + 1 }}
        </template>

        <template #title="{ record }">
          <a-link @click="goDetail(record)" hoverable>
            {{ record.title }}
          </a-link>
        </template>

        <template #authors="{ record }">
          <a-typography-text :ellipsis="{ rows: 1 }">
            {{ record.authors || '-' }}
          </a-typography-text>
        </template>

        <template #status="{ record }">
          <a-tag
            :color="statusColorMap[record.status] || 'gray'"
            size="small"
          >
            {{ statusTextMap[record.status] || record.status }}
          </a-tag>
        </template>

        <template #noteStatus="{ record }">
          <IconCheckCircle
            v-if="record.has_note"
            :size="18"
            style="color: rgb(var(--arcogreen-6))"
          />
          <IconFile
            v-else
            :size="18"
            style="color: var(--color-text-4)"
          />
        </template>

        <template #actions="{ record }">
          <a-space>
            <a-tooltip content="查看详情">
              <a-button type="text" size="mini" @click="goDetail(record)">
                <template #icon><IconEye /></template>
              </a-button>
            </a-tooltip>
            <a-popconfirm
              content="确定删除这篇论文吗？删除后不可恢复。"
              type="warning"
              @ok="confirmDelete(record)"
            >
              <a-tooltip content="删除">
                <a-button type="text" status="danger" size="mini">
                  <template #icon><IconDelete /></template>
                </a-button>
              </a-tooltip>
            </a-popconfirm>
          </a-space>
        </template>
      </a-table>

      <a-empty
        v-if="!loading && tableData.length === 0"
        description="暂无论文数据，去上传第一篇吧"
      >
        <template #extra>
          <a-button type="primary" @click="router.push('/upload')">
            上传论文
          </a-button>
        </template>
      </a-empty>
    </a-card>
  </div>
</template>

<style scoped>
.paper-library-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-card {
  border-radius: 8px;
}

.filter-card :deep(.arco-card-body) {
  padding: 16px;
}
</style>
