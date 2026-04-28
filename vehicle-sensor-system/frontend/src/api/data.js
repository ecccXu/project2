/**
 * 历史数据查询 API
 */
import request from './request'

/**
 * 查询历史传感器数据
 * @param {Object} params - 查询参数
 * @param {string} [params.node_id] - 节点ID筛选
 * @param {boolean} [params.is_abnormal] - 合规状态筛选
 * @param {number} [params.offset=0] - 分页偏移
 * @param {number} [params.limit=50] - 每页数量
 */
export function getHistoryData(params = {}) {
  return request.get('/api/data/history', { params })
}