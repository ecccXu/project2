/**
 * 历史报告 API
 */
import request from './request'

/**
 * 保存测试报告到数据库
 */
export function saveReport(payload) {
  return request.post('/api/reports/save', payload)
}

/**
 * 获取历史报告列表
 * @param {Object} params
 * @param {string} [params.node_id] - 节点ID筛选
 * @param {number} [params.offset=0] - 分页偏移
 * @param {number} [params.limit=20] - 每页数量
 */
export function getReportList(params = {}) {
  return request.get('/api/reports/list', { params })
}

/**
 * 获取指定报告详情
 */
export function getReportDetail(reportId) {
  return request.get(`/api/reports/${reportId}`)
}