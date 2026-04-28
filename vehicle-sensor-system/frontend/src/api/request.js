/**
 * Axios 请求封装
 *
 * 功能：
 *   1. 统一 baseURL 配置
 *   2. 请求/响应拦截器
 *   3. 统一错误处理
 *   4. 超时控制
 *
 * 使用方式：
 *   import request from '@/api/request'
 *   const data = await request.get('/api/nodes')
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'

// ==========================================
// 创建 Axios 实例
// ==========================================
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// ==========================================
// 请求拦截器
// ==========================================
request.interceptors.request.use(
  (config) => {
    // 这里可以统一加 token、loading 等
    // config.headers['Authorization'] = `Bearer ${token}`
    return config
  },
  (error) => {
    console.error('[Request Error]', error)
    return Promise.reject(error)
  }
)

// ==========================================
// 响应拦截器
// ==========================================
request.interceptors.response.use(
  (response) => {
    // 直接返回数据部分（脱去 axios 的外壳）
    return response.data
  },
  (error) => {
    // 统一错误处理
    let message = '请求失败'

    if (error.response) {
      // 服务器返回了错误状态码
      const { status, data } = error.response
      switch (status) {
        case 400:
          message = data?.detail || '请求参数错误'
          break
        case 404:
          message = '接口不存在'
          break
        case 500:
          message = '服务器内部错误'
          break
        default:
          message = data?.detail || `请求失败 (${status})`
      }
    } else if (error.request) {
      // 请求发出但无响应
      if (error.code === 'ECONNABORTED') {
        message = '请求超时，请检查网络'
      } else {
        message = '后端服务无响应，请确认后端已启动'
      }
    } else {
      // 其他错误
      message = error.message || '未知错误'
    }

    // 显示错误提示
    ElMessage.error(message)
    console.error('[Response Error]', error)

    return Promise.reject(error)
  }
)

export default request