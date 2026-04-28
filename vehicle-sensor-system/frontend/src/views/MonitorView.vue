<!-- frontend/src/views/MonitorView.vue -->
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getNodes, getNodeLatest } from '@/api'

// ==========================================
// 状态
// ==========================================
const availableNodes = ref([])
const selectedNode = ref('')
const monitorData = ref({})
const isAbnormal = ref(false)
const abnormalMsg = ref('')

// ==========================================
// 数据获取
// ==========================================
const fetchNodes = async () => {
  try {
    const res = await getNodes()
    availableNodes.value = res.nodes || []

    // 默认选中第一个节点
    if (availableNodes.value.length > 0 && !selectedNode.value) {
      selectedNode.value = availableNodes.value[0].node_id
    }
  } catch (e) {
    console.error('获取节点列表失败', e)
  }
}

const fetchMonitorData = async () => {
  if (!selectedNode.value) return
  try {
    const res = await getNodeLatest(selectedNode.value)
    monitorData.value = res.latest_data || {}
    isAbnormal.value = monitorData.value.is_abnormal || false
    abnormalMsg.value = monitorData.value.error_msg || ''
  } catch (e) {
    console.error('监控数据获取失败', e)
  }
}

// ==========================================
// 生命周期
// ==========================================
let nodesTimer = null
let monitorTimer = null

onMounted(() => {
  fetchNodes()
  nodesTimer = setInterval(fetchNodes, 5000)
  monitorTimer = setInterval(fetchMonitorData, 1500)
})

onUnmounted(() => {
  if (nodesTimer) clearInterval(nodesTimer)
  if (monitorTimer) clearInterval(monitorTimer)
})
</script>

<template>
  <div class="monitor-view">

    <!-- 工具栏：节点选择 -->
    <div class="toolbar">
      <span class="toolbar-label">监控节点：</span>
      <el-select
        v-model="selectedNode"
        placeholder="请选择节点"
        style="width: 220px"
        @change="fetchMonitorData"
      >
        <el-option
          v-for="n in availableNodes"
          :key="n.node_id"
          :label="n.node_id"
          :value="n.node_id"
        />
      </el-select>
      <el-tag
        v-if="availableNodes.length === 0"
        type="info"
        style="margin-left: 12px"
      >
        暂无在线节点，请启动模拟器或接入 ESP32
      </el-tag>
    </div>

    <!-- 异常告警横幅 -->
    <el-alert
      v-if="isAbnormal"
      :title="`⚠️ 数据异常告警：${abnormalMsg}`"
      type="error"
      :closable="false"
      style="margin-bottom: 16px"
    />

    <!-- 数据卡片网格 -->
    <div class="data-cards">
      <div class="data-card">
        <div class="card-label">车内温度</div>
        <div class="card-value temp">
          {{ monitorData.in_car_temp?.toFixed(1) ?? '--' }}
          <span class="unit">℃</span>
        </div>
      </div>

      <div class="data-card">
        <div class="card-label">车外温度</div>
        <div class="card-value temp">
          {{ monitorData.out_car_temp?.toFixed(1) ?? '--' }}
          <span class="unit">℃</span>
        </div>
      </div>

      <div class="data-card">
        <div class="card-label">车内湿度</div>
        <div class="card-value hum">
          {{ monitorData.humidity?.toFixed(1) ?? '--' }}
          <span class="unit">%RH</span>
        </div>
      </div>

      <div class="data-card">
        <div class="card-label">PM2.5</div>
        <div class="card-value pm">
          {{ monitorData.pm25?.toFixed(1) ?? '--' }}
          <span class="unit">μg/m³</span>
        </div>
      </div>

      <div class="data-card">
        <div class="card-label">CO₂ 浓度</div>
        <div class="card-value co2">
          {{ monitorData.co2?.toFixed(1) ?? '--' }}
          <span class="unit">ppm</span>
        </div>
      </div>

      <div class="data-card">
        <div class="card-label">硬件状态</div>
        <div
          class="card-value"
          :class="monitorData.status === 'FAULT' ? 'fault' : 'normal'"
        >
          {{ monitorData.status ?? 'UNKNOWN' }}
          <div class="card-extra">
            {{ monitorData.fault_code }}
          </div>
        </div>
      </div>

      <div class="data-card">
        <div class="card-label">传输延迟</div>
        <div class="card-value">
          {{ monitorData.latency_ms ?? '--' }}
          <span class="unit">ms</span>
        </div>
      </div>

      <div class="data-card">
        <div class="card-label">合规状态</div>
        <div
          class="card-value"
          :class="monitorData.is_abnormal ? 'fault' : 'normal'"
        >
          {{ monitorData.is_abnormal ? '⚠️ 超标' : '✅ 正常' }}
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.monitor-view {
  width: 100%;
}

/* 工具栏 */
.toolbar {
  display: flex;
  align-items: center;
  margin-bottom: var(--spacing-5);
  flex-wrap: wrap;
  gap: var(--spacing-3);
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

/* 数据卡片网格 */
.data-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--spacing-4);
}

.data-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-5);
  border-left: 4px solid var(--color-primary);
  transition: all var(--transition-normal);
  box-shadow: var(--shadow-sm);
}

.data-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.card-label {
  font-size: var(--font-xs);
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: var(--spacing-3);
  font-weight: var(--font-weight-medium);
}

.card-value {
  font-size: var(--font-xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  line-height: 1.2;
}

.card-extra {
  font-size: var(--font-xs);
  color: var(--text-tertiary);
  margin-top: var(--spacing-1);
  font-weight: var(--font-weight-normal);
}

.unit {
  font-size: var(--font-sm);
  color: var(--text-tertiary);
  margin-left: var(--spacing-1);
  font-weight: var(--font-weight-normal);
}

/* 不同传感器的色彩区分 */
.temp { color: #0EA5E9; }
.hum { color: #06B6D4; }
.pm { color: #F59E0B; }
.co2 { color: #8B5CF6; }
.normal { color: var(--color-success); }
.fault {
  color: var(--color-danger);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>