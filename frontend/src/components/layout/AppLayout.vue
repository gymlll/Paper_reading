<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  IconDashboard,
  IconBook,
  IconUpload,
  IconSettings,
  IconFile,
} from '@arco-design/web-vue/es/icon'
const router = useRouter()
const route = useRoute()

const menuItems = [
  { key: '/', label: '仪表盘', icon: IconDashboard },
  { key: '/papers', label: '论文库', icon: IconBook },
  { key: '/upload', label: '上传论文', icon: IconUpload },
  { key: '/settings', label: '设置', icon: IconSettings },
]

// 当前激活的菜单项：精确匹配，子路由也高亮父级
const selectedKeys = computed(() => {
  const path = route.path
  if (path.startsWith('/papers')) return ['/papers']
  return [path]
})

function handleMenuClick(key) {
  router.push(key)
}
</script>

<template>
  <div class="layout-container">
    <!-- 左侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-logo">
        <IconFile :size="22" style="color: rgb(var(--arcoblue-6))" />
        <span>Paper Notes</span>
      </div>
      <nav class="sidebar-menu">
        <a-menu
          :selected-keys="selectedKeys"
          :auto-open-selected="true"
          @menu-item-click="handleMenuClick"
          :style="{ width: '100%' }"
        >
          <a-menu-item
            v-for="item in menuItems"
            :key="item.key"
          >
            <template #icon>
              <component :is="item.icon" />
            </template>
            {{ item.label }}
          </a-menu-item>
        </a-menu>
      </nav>

      <!-- 侧边栏底部版本号 -->
      <div class="sidebar-footer">
        <a-typography-text type="secondary" style="font-size: 12px">
          Paper Notes v0.1
        </a-typography-text>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="main-area">
      <main class="main-content">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
.sidebar-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--color-border);
  text-align: center;
}

:deep(.arco-menu) {
  background: transparent;
}

:deep(.arco-menu-item) {
  border-radius: 4px;
  margin: 2px 8px;
}
</style>
