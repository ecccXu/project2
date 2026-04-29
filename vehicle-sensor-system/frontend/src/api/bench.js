/**
 * 台架测试相关 API
 */
import request from './request'

/**
 * 获取所有可用测试用例
 */
export function getBenchCases() {
  return request.get('/api/bench/cases')
}

/**
 * 启动台架测试
 * @param {Object} payload
 * @param {string} payload.node_id - 目标节点
 * @param {Array} payload.cases - 用例配置 [{id, params}, ...]
 */
export function runBench(payload) {
  return request.post('/api/bench/run', payload)
}

/**
 * 强制停止测试
 */
export function stopBench() {
  return request.post('/api/bench/stop')
}

/**
 * 获取台架运行状态
 */
export function getBenchStatus() {
  return request.get('/api/bench/status')
}

/**
 * 获取测试执行日志
 */
export function getBenchLogs() {
  return request.get('/api/bench/logs')
}

/**
 * 获取本次测试报告
 */
export function getBenchReport() {
  return request.get('/api/bench/report')
}

/**
 * 添加自定义测试用例
 */
export function addCustomCase(caseData) {
  return request.post('/api/bench/cases/custom', caseData)
}

/**
 * 删除自定义测试用例
 */
export function removeCustomCase(caseId) {
  return request.delete(`/api/bench/cases/custom/${caseId}`)
}