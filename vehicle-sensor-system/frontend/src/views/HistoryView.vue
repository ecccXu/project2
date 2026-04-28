<!-- frontend/src/views/HistoryView.vue -->
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getNodes, getHistoryData } from '@/api'

// ==========================================
// 状态
// ==========================================
const availableNodes = ref([])
const historyNode = ref('')
const historyAbnormal = ref(null)
const historyData = ref([])
const historyTotal = ref(0)
const historyPage = ref(1)
const historyPageSize = ref(20)
const historyLoading = ref(false)

// ==========================================
// 数据获取
// ==========================================
const fetchNodes = async () => {
  try {
    const res = await getNodes()
    availableNodes.value = res.nodes || []
  } catch (e) {
    console.error('获取节点列表失败', e)
  }
}

const fetchHistory = async () => {
  historyLoading.value = true
  try {
    const params = {
      limit: historyPageSize.value,
      offset: (historyPage.value - 1) * historyPageSize.value,
    }
    if (historyNode.value) params.node_id = historyNode.value
    if (historyAbnormal.value !== null) params.is_abnormal = historyAbnormal.value

    const res = await getHistoryData(params)
    historyData.value = res.data || []
    historyTotal.value = res.total || 0
  } catch (e) {
    ElMessage.error('历史数据获取失败')
  } finally {
    historyLoading.value = false
  }
}

const handlePageChange = (page) => {
  historyPage.value = page
  fetchHistory()
}

const resetFilter = () => {
  historyNode.value = ''
  historyAbnormal.value = null
  historyPage.value = 1
  fetchHistory()
}

// ==========================================
// 生命周期
// ==========================================
let nodesTimer = null

onMounted(() => {
  fetchNodes()
  fetchHistory()
  nodesTimer = setInterval(fetchNodes, 5000)
})

onUnmounted(() => {
  if (nodesTimer) clearInterval(nodesTimer)
})
</script>

<template>
  <div class="history-view">

    <!-- 筛选工具栏 -->
    <div class="toolbar">
      <span class="toolbar-label">节点筛选：</span>
      <el-select
        v-model="historyNode"
        placeholder="全部节点"
        clearable
        style="width: 180px"
      >
        <el-option
          v-for="n in availableNodes"
          :key="n.node_id"
          :label="n.node_id"
          :value="n.node_id"
        />
      </el-select>

      <span class="toolbar-label" style="margin-left: 16px">数据状态：</span>
      <el-select
        v-model="historyAbnormal"
        placeholder="全部"
        clearable
        style="width: 140px"
      >
        <el-option label="全部" :value="null" />
        <el-option label="仅异常" :value="true" />
        <el-option label="仅正常" :value="false" />
      </el-select>

      <div class="toolbar-actions">
        <el-button type="primary" @click="fetchHistory">
          <el-icon><Search /></el-icon>
          查询
        </el-button>
        <el-button @click="resetFilter">
          <el-icon><Refresh /></el-icon>
          重置
        </el-button>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="table-card">
      <el-table
        :data="historyData"
        v-loading="historyLoading"
        stripe
        border
        style="width: 100%"
        :row-class-name="({ row }) => row.is_abnormal ? 'abnormal-row' : ''"
      >
        <el-table-column prop="sensor_id" label="节点 ID" width="140" />

        <el-table-column prop="in_car_temp" label="车内温(℃)" width="100">
          <template #default="{ row }">
            {{ row.in_car_temp?.toFixed(1) ?? '--' }}
          </template>
        </el-table-column>

        <el-table-column prop="out_car_temp" label="车外温(℃)" width="100">
          <template #default="{ row }">
            {{ row.out_car_temp?.toFixed(1) ?? '--' }}
          </template>
        </el-table-column>

        <el-table-column prop="humidity" label="湿度(%)" width="90">
          <template #default="{ row }">
            {{ row.humidity?.toFixed(1) ?? '--' }}
          </template>
        </el-table-column>

        <el-table-column prop="pm25" label="PM2.5" width="90">
          <template #default="{ row }">
            {{ row.pm25?.toFixed(1) ?? '--' }}
          </template>
        </el-table-column>

        <el-table-column prop="co2" label="CO₂(ppm)" width="100">
          <template #default="{ row }">
            {{ row.co2?.toFixed(1) ?? '--' }}
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'FAULT' ? 'danger' : 'success'"
              size="small"
            >
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="is_abnormal" label="合规" width="80">
          <template #default="{ row }">
            <el-tag
              :type="row.is_abnormal ? 'danger' : 'success'"
              size="small"
            >
              {{ row.is_abnormal ? '超标' : '正常' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column
          prop="error_msg"
          label="异常详情"
          show-overflow-tooltip
        />

        <el-table-column prop="latency_ms" label="延迟(ms)" width="90" />
        <el-table-column prop="server_time" label="采集时间" width="170" />
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="historyPage"
          :page-size="historyPageSize"
          :total="historyTotal"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </div>

  </div>
</template>

<style scoped>
.history-view {
  width: 100%;
}

/* 工具栏 */
.toolbar {
  display: flex;
  align-items: center;
  margin-bottom: var(--spacing-5);
  flex-wrap: wrap;
  gap: var(--spacing-2);
  padding: var(--spacing-4);
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
}

.toolbar-label {
  color: var(--text-secondary);
  font-size: var(--font-sm);
  font-weight: var(--font-weight-medium);
}

.toolbar-actions {
  margin-left: auto;
  display: flex;
  gap: var(--spacing-2);
}

/* 表格卡片 */
.table-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: var(--spacing-5);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--spacing-4);
  padding-top: var(--spacing-3);
  border-top: 1px solid var(--border-light);
}

/* 异常行高亮 */
:deep(.abnormal-row) {
  background-color: var(--color-danger-bg) !important;
}

:deep(.abnormal-row:hover > td) {
  background-color: var(--color-danger-light) !important;
}
</style>