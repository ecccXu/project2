/**
 * 路由配置
 *
 * 路由结构：
 *   / (布局) → 重定向到 /monitor
 *     ├── /monitor   实时监控
 *     ├── /bench     测试执行
 *     ├── /history   历史数据
 *     └── /reports   历史报告
 */

import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/monitor',
    children: [
      {
        path: 'monitor',
        name: 'Monitor',
        component: () => import('@/views/MonitorView.vue'),
        meta: {
          title: '实时监控',
          icon: 'Monitor',
        }
      },
      {
        path: 'bench',
        name: 'TestBench',
        component: () => import('@/views/TestBenchView.vue'),
        meta: {
          title: '测试执行',
          icon: 'Operation',
        }
      },
      {
        path: 'history',
        name: 'History',
        component: () => import('@/views/HistoryView.vue'),
        meta: {
          title: '历史数据',
          icon: 'DataAnalysis',
        }
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/ReportView.vue'),
        meta: {
          title: '历史报告',
          icon: 'Document',
        }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/monitor'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫：动态修改页面标题
router.beforeEach((to, from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} - 车载传感器测试系统`
  }
  next()
})

export default router