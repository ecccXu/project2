<!-- src/App.vue -->
<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

const API_BASE = 'http://127.0.0.1:8000'

// --- 状态定义 ---
const benchStatus = ref({
  is_running: false,
  current_case: '等待启动',
  progress: '0/4',
  results_summary: []
})
const terminalLogs = ref([])
const realtimePool = ref({ latest_data_snapshot: {} })
const reportVisible = ref(false)
const reportData = ref(null)
const reportChartInstance = ref(null)

let statusTimer = null
let poolTimer = null
const terminalRef = ref(null) // 终端 DOM 引用，用于自动滚底

// 预定义的用例列表，与后端保持一致
const caseList = [
  { id: 1, name: '极限温度阶跃响应测试' },
  { id: 2, name: '硬件断路故障诊断测试' },
  { id: 3, name: '复杂工况动态抗扰测试' },
  { id: 4, name: '安全通信链路抗篡改测试' }
]

// --- 核心动作 ---
const startBench = async () => {
  terminalLogs.value = []
  benchStatus.value = { is_running: true, current_case: '系统初始化...', progress: '0/4', results_summary: [] }
  reportVisible.value = false
  await axios.post(`${API_BASE}/api/bench/run`)
  startPolling()
}

// --- 轮询逻辑 ---
const startPolling = () => {
  stopPolling()
  statusTimer = setInterval(async () => {
    try {
      // 获取状态
      const statusRes = await axios.get(`${API_BASE}/api/bench/status`)
      const newStatus = statusRes.data
      benchStatus.value = newStatus

      // 获取日志
      const logRes = await axios.get(`${API_BASE}/api/bench/logs`)
      terminalLogs.value = logRes.data.logs

      // 滚动到底部
      await nextTick()
      if (terminalRef.value) {
        terminalRef.value.scrollTop = terminalRef.value.scrollHeight
      }

      // 检测是否结束
      if (!newStatus.is_running && newStatus.results_summary.length === caseList.length) {
        stopPolling()
        fetchFinalReport()
      }
    } catch (e) { console.error('轮询错误', e) }
  }, 800) // 每 800ms 刷新一次，模拟终端实时感
}

const stopPolling = () => {
  if (statusTimer) clearInterval(statusTimer)
  statusTimer = null
}

const fetchFinalReport = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/bench/report`)
    if (res.data.status === 'success') {
      reportData.value = res.data
      reportVisible.value = true
      nextTick(() => initReportChart())
    }
  } catch (e) { console.error('获取报告失败', e) }
}

const fetchPoolData = () => {
  axios.get(`${API_BASE}/api/debug/pool`).then(res => {
    realtimePool.value = res.data
  }).catch(() => {})
}

// --- 报告图表 ---
const initReportChart = () => {
  if (!reportData.value) return
  const dom = document.getElementById('reportPieChart')
  if (!dom) return
  if (reportChartInstance.value) reportChartInstance.value.dispose()

  reportChartInstance.value = echarts.init(dom)
  reportChartInstance.value.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, fontSize: 16, fontWeight: 'bold', formatter: '{b}\n{d}%' },
      data: [
        { value: reportData.value.pass_count, name: '通过 (PASS)', itemStyle: { color: '#67C23A' } },
        { value: reportData.value.fail_count, name: '失败 (FAIL)', itemStyle: { color: '#F56C6C' } }
      ]
    }]
  })
}

// 获取用例状态的辅助函数
const getCaseStatus = (caseName) => {
  const found = benchStatus.value.results_summary.find(r => r.case.includes(caseName))
  if (!found) {
    // 如果当前正在跑这个用例
    if (benchStatus.value.current_case.includes(caseName)) return 'RUNNING'
    return 'PENDING'
  }
  return found.status
}

// --- 生命周期 ---
onMounted(() => {
  fetchPoolData()
  poolTimer = setInterval(fetchPoolData, 1500)
})
onUnmounted(() => {
  stopPolling()
  if (poolTimer) clearInterval(poolTimer)
  if (reportChartInstance.value) reportChartInstance.value.dispose()
})
</script>

<template>
  <div class="bench-container">
    <!-- 顶部标题栏 -->
    <div class="header">
      <div class="header-left">
        <span class="logo">⚡</span>
        <span class="title">车载环境传感器 | 自动化台架测试系统 v1.0</span>
      </div>
      <div class="header-right">
        <el-button
          type="primary"
          size="large"
          @click="startBench"
          :loading="benchStatus.is_running"
          style="background: #409EFF; border-color: #409EFF;"
        >
          {{ benchStatus.is_running ? '台架运行中...' : '启动台架测试' }}
        </el-button>
      </div>
    </div>

    <!-- 主体三栏布局 -->
    <div class="main-layout">

      <!-- 左侧：用例树 -->
      <div class="panel left-panel">
        <div class="panel-title">测试用例集 ({{ benchStatus.progress }})</div>
        <div class="case-list">
          <div
            v-for="c in caseList"
            :key="c.id"
            class="case-item"
            :class="{ active: getCaseStatus(c.name) === 'RUNNING' }"
          >
            <span class="status-icon">
              <span v-if="getCaseStatus(c.name) === 'PENDING'" class="dot pending"></span>
              <span v-else-if="getCaseStatus(c.name) === 'RUNNING'" class="dot running"></span>
              <span v-else-if="getCaseStatus(c.name) === 'PASS'" class="dot pass">✓</span>
              <span v-else class="dot fail">✕</span>
            </span>
            <span class="case-name">{{ c.name }}</span>
          </div>
        </div>
      </div>

      <!-- 中间：终端日志 -->
      <div class="panel center-panel">
        <div class="panel-title">执行控制台</div>
        <div ref="terminalRef" class="terminal">
          <div v-if="terminalLogs.length === 0" class="terminal-placeholder">
            > 等待启动台架测试任务...
          </div>
          <div v-for="(log, index) in terminalLogs" :key="index" class="log-line" v-html="formatLog(log)"></div>
        </div>
      </div>

      <!-- 右侧：实时数据旁路 -->
      <div class="panel right-panel">
        <div class="panel-title">数据旁路监控</div>
        <div class="data-cards">
          <div class="data-card">
            <div class="label">车内温度</div>
            <div class="value temp">{{ realtimePool.latest_data_snapshot?.in_car_temp?.toFixed(1) || '0.0' }}<span class="unit">℃</span></div>
          </div>
          <div class="data-card">
            <div class="label">PM2.5</div>
            <div class="value pm">{{ realtimePool.latest_data_snapshot?.pm25?.toFixed(1) || '0.0' }}<span class="unit">ug/m³</span></div>
          </div>
          <div class="data-card">
            <div class="label">CO2</div>
            <div class="value co2">{{ realtimePool.latest_data_snapshot?.co2?.toFixed(1) || '0.0' }}<span class="unit">ppm</span></div>
          </div>
          <div class="data-card full-width">
            <div class="label">硬件状态</div>
            <div class="value" :class="realtimePool.latest_data_snapshot?.status === 'FAULT' ? 'fault' : 'normal'">
              {{ realtimePool.latest_data_snapshot?.status || 'NORMAL' }}
              <span style="font-size: 12px; margin-left: 5px; color: #999;">{{ realtimePool.latest_data_snapshot?.fault_code }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 测试报告弹窗 -->
    <el-dialog
      v-model="reportVisible"
      title="台架深度测试分析报告"
      width="70%"
      :close-on-click-modal="false"
      class="report-dialog"
    >
      <div v-if="reportData" class="report-container">
        <el-row :gutter="20">
          <el-col :span="8">
            <div id="reportPieChart" style="height: 250px;"></div>
          </el-col>
          <el-col :span="16">
            <el-table :data="reportData.details" stripe border style="width: 100%" max-height="250">
              <el-table-column prop="case" label="用例名称" width="220" />
              <el-table-column prop="status" label="结果" width="80">
                <template #default="scope">
                  <el-tag :type="scope.row.status === 'PASS' ? 'success' : 'danger'" size="small">{{ scope.row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="duration" label="耗时" width="80" />
              <el-table-column prop="details" label="详细技术指标" show-overflow-tooltip />
            </el-table>
          </el-col>
        </el-row>
      </div>
      <template #footer>
        <el-button @click="reportVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
export default {
  methods: {
    // 简单的日志高亮渲染
    formatLog(log) {
      if (log.includes('FAIL') || log.includes('错误') || log.includes('异常')) {
        return `<span style="color: #F56C6C;">${log}</span>`
      } else if (log.includes('PASS') || log.includes('成功') || log.includes('有效')) {
        return `<span style="color: #67C23A;">${log}</span>`
      } else if (log.includes('-> 下发指令')) {
        return `<span style="color: #409EFF;">${log}</span>`
      }
      return log
    }
  }
}
</script>

<style scoped>
/* 全局深色背景 */
.bench-container {
  background: #1e1e1e;
  color: #d4d4d4;
  height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  overflow: hidden;
}

/* 顶部栏 */
.header {
  height: 50px;
  background: #252526;
  border-bottom: 1px solid #3e3e42;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  flex-shrink: 0;
}
.header-left { display: flex; align-items: center; gap: 10px; }
.logo { font-size: 20px; }
.title { font-size: 15px; color: #cccccc; font-weight: 500; }

/* 主体布局 */
.main-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
  padding: 10px;
  gap: 10px;
}

/* 面板基础样式 */
.panel {
  background: #252526;
  border: 1px solid #3e3e42;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
}
.panel-title {
  padding: 8px 15px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #bbbbbb;
  border-bottom: 1px solid #3e3e42;
  background: #2d2d30;
  font-weight: bold;
}

/* 左侧面板 */
.left-panel { width: 25%; }
.case-list { padding: 10px 0; overflow-y: auto; flex: 1; }
.case-item {
  padding: 10px 15px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #9cdcfe;
  border-left: 3px solid transparent;
}
.case-item.active {
  background: #37373d;
  border-left-color: #409EFF;
}
.status-icon { width: 20px; text-align: center; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
.dot.pending { background: #6e7681; }
.dot.running { background: #409EFF; animation: blink 1s infinite; }
.dot.pass { color: #67C23A; font-size: 14px; background: transparent; width: auto; }
.dot.fail { color: #F56C6C; font-size: 14px; background: transparent; width: auto; }

@keyframes blink { 50% { opacity: 0.2; } }

/* 中间终端 */
.center-panel { flex: 1; }
.terminal {
  flex: 1;
  padding: 15px;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  overflow-y: auto;
  background: #1e1e1e;
}
.terminal-placeholder { color: #6e7681; }
.log-line { white-space: pre-wrap; word-break: break-all; }

/* 右侧面板 */
.right-panel { width: 20%; }
.data-cards { padding: 10px; display: flex; flex-direction: column; gap: 10px; }
.data-card {
  background: #2d2d30;
  padding: 12px;
  border-radius: 4px;
  border-left: 3px solid #3e3e42;
}
.data-card.full-width { border-left-color: #67C23A; }
.label { font-size: 11px; color: #8b949e; margin-bottom: 5px; text-transform: uppercase; }
.value { font-size: 20px; font-weight: bold; color: #d2d8de; }
.unit { font-size: 12px; color: #8b949e; margin-left: 4px; font-weight: normal; }
.temp { color: #4fc1ff; }
.pm { color: #e5c07b; }
.co2 { color: #c678dd; }
.normal { color: #67C23A; }
.fault { color: #F56C6C; animation: blink 1s infinite; }

/* 报告弹窗覆盖样式 (强制亮色以便阅读和打印) */
:deep(.report-dialog .el-dialog) {
  background: #fff;
  color: #333;
  border-radius: 8px;
}
:deep(.report-dialog .el-dialog__header) {
  border-bottom: 1px solid #eee;
}
:deep(.report-dialog .el-dialog__title) {
  color: #333;
  font-weight: bold;
}
</style>