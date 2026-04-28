/**
 * 节点相关 API
 */
import request from './request'

/**
 * 获取所有在线节点列表
 */
export function getNodes() {
  return request.get('/api/nodes')
}

/**
 * 获取指定节点最新数据
 */
export function getNodeLatest(nodeId) {
  return request.get(`/api/nodes/${nodeId}`)
}

/**
 * 调试：查看节点内存数据池
 */
export function getNodePool(nodeId) {
  return request.get(`/api/debug/pool/${nodeId}`)
}