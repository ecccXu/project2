// src/main.js
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

// ============================================================
// 样式引入顺序（重要！后引入的会覆盖先引入的）
// ============================================================
// 1. Element Plus 默认样式
import 'element-plus/dist/index.css'

// 2. 全局设计系统
import './styles/variables.css'   // CSS 变量（必须最先）
import './styles/reset.css'        // CSS 重置
import './styles/theme.css'        // 主题样式（覆盖 Element Plus）

// 3. 项目原有 style.css
import './style.css'

import App from './App.vue'

const app = createApp(App)

// 注册 Element Plus
app.use(ElementPlus)

// 全局注册所有 Element Plus 图标（后续阶段会用到）
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')