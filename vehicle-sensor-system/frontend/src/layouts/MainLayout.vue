<!-- frontend/src/layouts/MainLayout.vue -->
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getNodes } from '@/api'

const route = useRoute()
const router = useRouter()

// ==========================================
// 侧边栏状态
// ==========================================
const isCollapsed = ref(false)

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

// ==========================================
// 导航菜单（与路由配置同步）
// ==========================================
const menuItems = [
  {
    path: '/monitor',
    name: '实时监控',
    icon: 'Monitor',
    description: '传感器数据实时展示'
  },
  {
    path: '/bench',
    name: '测试执行',
    icon: 'Operation',
    description: '自动化台架测试'
  },
  {
    path: '/history',
    name: '历史数据',
    icon: 'DataAnalysis',
    description: '历史数据查询分析'
  },
  {
    path: '/reports',
    name: '历史报告',
    icon: 'Document',
    description: '测试报告管理'
  },
]

// 当前激活的菜单
const activePath = computed(() => route.path)

// 当前页面标题
const currentTitle = computed(() => {
  const item = menuItems.find(m => m.path === activePath.value)
  return item?.name || '系统'
})

// 切换菜单
const handleMenuClick = (path) => {
  if (path !== activePath.value) {
    router.push(path)
  }
}

// ==========================================
// 在线节点数（顶部状态栏）
// ==========================================
const onlineNodeCount = ref(0)
let nodesTimer = null

const fetchOnlineNodes = async () => {
  try {
    const res = await getNodes()
    onlineNodeCount.value = res.nodes?.length || 0
  } catch (e) {
    onlineNodeCount.value = 0
  }
}

onMounted(() => {
  fetchOnlineNodes()
  nodesTimer = setInterval(fetchOnlineNodes, 5000)
})

onUnmounted(() => {
  if (nodesTimer) clearInterval(nodesTimer)
})
</script>

<template>
  <div class="layout-container">

    <!-- ==================== 侧边栏 ==================== -->
    <aside
      class="sidebar"
      :class="{ 'is-collapsed': isCollapsed }"
    >

      <!-- Logo 区域 -->
      <div class="sidebar-logo">
        <div class="logo-icon">⚡</div>
        <transition name="fade">
          <div v-if="!isCollapsed" class="logo-text">
            <div class="logo-title">车载传感器</div>
            <div class="logo-subtitle">测试系统</div>
          </div>
        </transition>
      </div>

      <!-- 导航菜单 -->
      <nav class="sidebar-nav">
        <div
          v-for="item in menuItems"
          :key="item.path"
          class="nav-item"
          :class="{ 'is-active': activePath === item.path }"
          @click="handleMenuClick(item.path)"
          :title="isCollapsed ? item.name : ''"
        >
          <el-icon class="nav-icon">
            <component :is="item.icon" />
          </el-icon>
          <transition name="fade">
            <span v-if="!isCollapsed" class="nav-text">{{ item.name }}</span>
          </transition>
        </div>
      </nav>

      <!-- 折叠按钮 -->
      <div class="sidebar-footer">
        <div class="collapse-btn" @click="toggleCollapse">
          <el-icon>
            <Fold v-if="!isCollapsed" />
            <Expand v-else />
          </el-icon>
          <transition name="fade">
            <span v-if="!isCollapsed">折叠菜单</span>
          </transition>
        </div>
      </div>

    </aside>

    <!-- ==================== 主内容区 ==================== -->
    <div class="main-wrapper">

      <!-- 顶部栏 -->
      <header class="main-header">
        <div class="header-left">
          <h2 class="page-title">{{ currentTitle }}</h2>
        </div>

        <div class="header-right">
          <div class="status-badge">
            <span class="status-dot" :class="{ 'is-online': onlineNodeCount > 0 }" />
            <span class="status-text">
              在线节点：<strong>{{ onlineNodeCount }}</strong> 个
            </span>
          </div>
        </div>
      </header>

      <!-- 路由出口（动态加载 Views）-->
      <main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>

    </div>

  </div>
</template>

<style scoped>
/* ==================== 整体布局 ==================== */
.layout-container {
  display: flex;
  width: 100%;
  height: 100vh;
  background: var(--bg-page);
}

/* ==================== 侧边栏 ==================== */
.sidebar {
  width: var(--sidebar-width);
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width var(--transition-normal);
  box-shadow: var(--shadow-sm);
  z-index: var(--z-sidebar);
}

.sidebar.is-collapsed {
  width: var(--sidebar-width-collapsed);
}

/* Logo 区域 */
.sidebar-logo {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-5) var(--spacing-4);
  border-bottom: 1px solid var(--border-color);
  height: 72px;
  overflow: hidden;
}

.logo-icon {
  font-size: 28px;
  color: var(--color-primary);
  flex-shrink: 0;
  width: 32px;
  text-align: center;
}

.logo-text {
  flex: 1;
  overflow: hidden;
}

.logo-title {
  font-size: var(--font-md);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  line-height: 1.2;
  white-space: nowrap;
}

.logo-subtitle {
  font-size: var(--font-xs);
  color: var(--text-tertiary);
  margin-top: 2px;
  white-space: nowrap;
}

/* 导航菜单 */
.sidebar-nav {
  flex: 1;
  padding: var(--spacing-3) var(--spacing-2);
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3) var(--spacing-3);
  margin-bottom: var(--spacing-1);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-secondary);
  font-size: var(--font-base);
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-fast);
  position: relative;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--color-primary);
}

.nav-item.is-active {
  background: var(--color-primary-lighter);
  color: var(--color-primary);
  font-weight: var(--font-weight-semibold);
}

.nav-item.is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  background: var(--color-primary);
  border-radius: 0 2px 2px 0;
}

.nav-icon {
  font-size: 18px;
  flex-shrink: 0;
  width: 20px;
}

.nav-text {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
}

/* 折叠按钮 */
.sidebar-footer {
  border-top: 1px solid var(--border-color);
  padding: var(--spacing-3);
}

.collapse-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-3);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-tertiary);
  font-size: var(--font-sm);
  transition: all var(--transition-fast);
}

.collapse-btn:hover {
  background: var(--bg-hover);
  color: var(--color-primary);
}

/* ==================== 主内容区 ==================== */
.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

/* 顶部栏 */
.main-header {
  height: var(--header-height);
  background: var(--bg-header);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-6);
  flex-shrink: 0;
  z-index: var(--z-header);
  box-shadow: var(--shadow-sm);
}

.page-title {
  font-size: var(--font-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: 6px 14px;
  background: var(--color-primary-lighter);
  border-radius: var(--radius-full);
  font-size: var(--font-sm);
  color: var(--color-primary);
  font-weight: var(--font-weight-medium);
}

.status-dot {
  width: 8px;
  height: 8px;
  background: var(--text-disabled);
  border-radius: 50%;
}

.status-dot.is-online {
  background: var(--color-success);
  box-shadow: 0 0 6px var(--color-success);
  animation: pulse 2s infinite;
}

.status-text strong {
  font-weight: var(--font-weight-bold);
}

/* 主内容 */
.main-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-6);
}

/* ==================== 动画 ==================== */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-fast);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.page-enter-active,
.page-leave-active {
  transition: all var(--transition-normal);
}

.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>