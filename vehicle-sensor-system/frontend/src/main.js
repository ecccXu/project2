// src/main.js
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

// ============================================================
// 样式引入顺序
// ============================================================
import 'element-plus/dist/index.css'
import './styles/variables.css'
import './styles/reset.css'
import './styles/theme.css'
import './style.css'

import App from './App.vue'
import router from './router'   // 🆕 引入路由

const app = createApp(App)

// 注册插件
app.use(ElementPlus)
app.use(router)                  // 🆕 使用路由

// 全局注册 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')