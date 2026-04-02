<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { IconSun, IconMoon } from '@arco-design/web-vue/es/icon'

const props = defineProps({
  title: {
    type: String,
    default: '仪表盘',
  },
})

const route = useRoute()

// 亮色/暗色主题切换
const isDark = computed({
  get() {
    return document.body.getAttribute('arco-theme') === 'dark'
  },
  set(val) {
    if (val) {
      document.body.setAttribute('arco-theme', 'dark')
    } else {
      document.body.removeAttribute('arco-theme')
    }
  },
})

// 面包屑导航
const breadcrumbs = computed(() => {
  const crumbs = [{ label: '首页', path: '/' }]
  if (route.path !== '/') {
    crumbs.push({ label: props.title, path: route.path })
  }
  return crumbs
})
</script>

<template>
  <header class="main-header">
    <div class="header-left">
      <a-breadcrumb>
        <a-breadcrumb-item
          v-for="(crumb, index) in breadcrumbs"
          :key="index"
        >
          <router-link v-if="crumb.path && index < breadcrumbs.length - 1" :to="crumb.path">
            {{ crumb.label }}
          </router-link>
          <span v-else>{{ crumb.label }}</span>
        </a-breadcrumb-item>
      </a-breadcrumb>
    </div>

    <div class="header-right">
      <a-tooltip :content="isDark ? '切换亮色模式' : '切换暗色模式'">
        <a-switch
          v-model="isDark"
          :checked-value="true"
          :unchecked-value="false"
        >
          <template #checked-icon>
            <IconMoon />
          </template>
          <template #unchecked-icon>
            <IconSun />
          </template>
        </a-switch>
      </a-tooltip>
    </div>
  </header>
</template>

<style scoped>
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
