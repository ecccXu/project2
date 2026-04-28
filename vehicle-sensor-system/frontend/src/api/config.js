/**
 * 系统配置 API
 */
import request from './request'

/**
 * 获取当前告警阈值
 */
export function getThresholds() {
  return request.get('/api/config/thresholds')
}

/**
 * 更新告警阈值
 */
export function updateThresholds(payload) {
  return request.put('/api/config/thresholds', payload)
}