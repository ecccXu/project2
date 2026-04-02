<!-- src/App.vue -->
<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

const API_BASE = 'http://127.0.0.1:8000'

// --- 状态定义 ---
const benchStatus = ref({
  is_running: false,
  current_case: '等待启动',
  progress: '0/0',
  results_summary: []
})
const terminalLogs = ref([])
const realtimePool = ref({ latest_data_snapshot: {} })
const reportVisible = ref(false)
const reportData = ref(null)
const reportChartInstance = ref(null)

let statusTimer = null
let poolTimer = null
const terminalRef = ref(null)

// --- 新增：用例编排相关状态 ---
const caseTemplates = ref([])      // 从后端拉取的原始用例元数据
const selectedCaseIds = ref([])    // 被勾选的用例 ID 数组
const drawerVisible = ref(false)   // 参数编辑抽屉状态
const editingCase = ref(null)      // 当前正在编辑参数的用例对象
const editingParams = ref({})      // 当前编辑框内的参数副本

// --- 核心动作 ---
const startBench = async () => {
  if (selectedCaseIds.value.length === 0) {
    alert('请至少勾选一个测试用例！')
    return
  }

  terminalLogs.value = []
  benchStatus.value = { is_running: true, current_case: '系统初始化...', progress: '0/0', results_summary: [] }
  reportVisible.value = false

  // 【核心改造】：组装前端编排好的配置列表
  const payload = selectedCaseIds.value.map(caseId => {
    // 找到该用例的模板数据，获取用户修改过的参数
    const template = caseTemplates.value.find(c => c.id === caseId)
    return {
      id: caseId,
      params: template ? template.current_params : {}
    }
  })

  // 发送给后端动态执行
  await axios.post(`${API_BASE}/api/bench/run`, payload)
  startPolling()
}

// --- 新增：用例编排逻辑 ---
const fetchCases = async () => {
  const res = await axios.get(`${API_BASE}/api/bench/cases`)
  if (res.data && res.data.cases) {
    // 初始化用例模板，为每个用例挂载一个 current_params 用于记录用户修改
    caseTemplates.value = res.data.cases.map(c => ({
      ...c,
      current_params: { ...c.default_params } // 深拷贝默认参数作为当前参数
    }))
  }
}

const handleCaseClick = (caseItem) => {
  editingCase.value = caseItem
  // 每次打开抽屉时，拿到当前的参数作为表单的初始值
  editingParams.value = { ...caseItem.current_params }
  drawerVisible.value = true
}

const saveParams = () => {
  // 将抽屉里修改的值，保存回模板的 current_params 中
  if (editingCase.value) {
    editingCase.value.current_params = { ...editingParams.value }
  }
  drawerVisible.value = false
}

// --- 轮询与报告逻辑 (保持不变) ---
const startPolling = () => {
  stopPolling()
  statusTimer = setInterval(async () => {
    try {
      const statusRes = await axios.get(`${API_BASE}/api/bench/status`)
      benchStatus.value = statusRes.data
      const logRes = await axios.get(`${API_BASE}/api/bench/logs`)
      terminalLogs.value = logRes.data.logs
      await nextTick()
      if (terminalRef.value) terminalRef.value.scrollTop = terminalRef.value.scrollHeight
      if (!benchStatus.value.is_running && benchStatus.value.results_summary.length > 0) {
        stopPolling()
        fetchFinalReport()
      }
    } catch (e) { console.error('轮询错误', e) }
  }, 800)
}
const stopPolling = () => { if (statusTimer) clearInterval(statusTimer); statusTimer = null }

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
  axios.get(`${API_BASE}/api/debug/pool`).then(res => { realtimePool.value = res.data }).catch(() => {})
}

const initReportChart = () => {
  if (!reportData.value) return
  const dom = document.getElementById('reportPieChart')
  if (!dom) return
  if (reportChartInstance.value) reportChartInstance.value.dispose()
  reportChartInstance.value = echarts.init(dom)
  reportChartInstance.value.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['40%', '70%'], avoidLabelOverlap: false,
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, fontSize: 16, fontWeight: 'bold', formatter: '{b}\n{d}%' },
      data: [
        { value: reportData.value.pass_count, name: '通过', itemStyle: { color: '#67C23A' } },
        { value: reportData.value.fail_count, name: '失败', itemStyle: { color: '#F56C6C' } }
      ]
    }]
  })
}

const getCaseStatus = (caseId) => {
  // 匹配逻辑需要模糊匹配，因为后端返回的 case 名字带了动态参数后缀
  const found = benchStatus.value.results_summary.find(r => r.case.includes(caseId))
  if (!found) {
    if (benchStatus.value.current_case.includes(caseId)) return 'RUNNING'
    return 'PENDING'
  }
  return found.status
}

// --- 生命周期 ---
onMounted(() => {
  fetchCases()  // 启动时先拉取用例列表
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
    <div class="header">
      <div class="header-left">
        <span class="logo">⚡</span>
        <span class="title">车载环境传感器 | 自动化台架测试系统 v2.0</span>
      </div>
      <div class="header-right">
        <!-- 按钮动态显示勾选数量 -->
        <el-button
          type="primary"
          size="large"
          @click="startBench"
          :loading="benchStatus.is_running"
          :disabled="selectedCaseIds.length === 0"
        >
          {{ benchStatus.is_running ? '台架运行中...' : `执行选中用例 (${selectedCaseIds.length})` }}
        </el-button>
      </div>
    </div>

    <div class="main-layout">
      <!-- 左侧：可编排用例树 -->
      <div class="panel left-panel">
        <div class="panel-title">测试用例编排</div>
        <div class="case-list">
          <!-- 基于后端拉取的数据动态渲染 -->
          <div
            v-for="c in caseTemplates"
            :key="c.id"
            class="case-item"
            :class="{ active: getCaseStatus(c.id) === 'RUNNING' }"
          >
            <el-checkbox
              v-model="selectedCaseIds"
              :label="c.id"
              :disabled="benchStatus.is_running"
              style="margin-right: 10px;"
            />
            <!-- 点击名称打开参数抽屉 -->
            <span class="case-name" @click="handleCaseClick(c)" title="点击编辑参数">
              {{ c.name }}
            </span>
            <!-- 状态图标 -->
            <span class="status-icon" style="margin-left: auto;">
              <span v-if="getCaseStatus(c.id) === 'PENDING'" class="dot pending"></span>
              <span v-else-if="getCaseStatus(c.id) === 'RUNNING'" class="dot running"></span>
              <span v-else-if="getCaseStatus(c.id) === 'PASS'" class="dot pass">✓</span>
              <span v-else class="dot fail">✕</span>
            </span>
          </div>
        </div>
      </div>

      <!-- 中间：终端日志 -->
      <div class="panel center-panel">
        <div class="panel-title">执行控制台</div>
        <div ref="terminalRef" class="terminal">
          <div v-if="terminalLogs.length === 0" class="terminal-placeholder">
            > 请在左侧勾选用例并配置参数，点击"执行选中用例"开始测试...
          </div>
          <div v-for="(log, index) in terminalLogs" :key="index" class="log-line" v-html="formatLog(log)"></div>
        </div>
      </div>

      <!-- 右侧：实时数据旁路 (保持不变) -->
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

    <!-- 新增：参数编辑抽屉 -->
    <el-drawer v-model="drawerVisible" title="用例参数配置" direction="rtl" size="300px">
      <div v-if="editingCase" style="padding: 0 10px;">
        <h4 style="color: #409EFF; margin-bottom: 20px;">{{ editingCase.name }}</h4>
        <p style="color: #8b949e; font-size: 12px; margin-bottom: 20px;">修改以下参数将覆盖默认值，仅影响本次测试执行。</p>
        <el-form label-position="top" size="default">
          <el-form-item
            v-for="(value, key) in editingParams"
            :key="key"
            :label="key"
          >
            <el-input
              v-model="editingParams[key]"
              type="number"
              placeholder="请输入数值"
            ></el-input>
          </el-form-item>
          <!-- 处理无参数的用例 -->
          <div v-if="Object.keys(editingParams).length === 0" style="color: #6e7681; text-align: center; margin-top: 30px;">
            该用例无 customizable 参数
          </div>
        </el-form>
        <el-button type="primary" @click="saveParams" style="width: 100%; margin-top: 20px;">保存并关闭</el-button>
      </div>
    </el-drawer>

    <!-- 测试报告弹窗 (保持不变) -->
    <el-dialog v-model="reportVisible" title="台架深度测试分析报告" width="70%" :close-on-click-modal="false" class="report-dialog">
      <div v-if="reportData" class="report-container">
        <el-row :gutter="20">
          <el-col :span="8"><div id="reportPieChart" style="height: 250px;"></div></el-col>
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
      <template #footer><el-button @click="reportVisible = false">关闭</el-button></template>
    </el-dialog>
  </div>
</template>

<script>
export default {
  methods: {
    formatLog(log) {
      if (log.includes('FAIL') || log.includes('错误') || log.includes('异常')) return `<span style="color: #F56C6C;">${log}</span>`
      if (log.includes('PASS') || log.includes('成功') || log.includes('有效')) return `<span style="color: #67C23A;">${log}</span>`
      if (log.includes('-> 下发指令')) return `<span style="color: #409EFF;">${log}</span>`
      return log
    }
  }
}
</script>

<style scoped>
/* 纯暗色风格保持完全不变 */
.bench-container { background: #1e1e1e; color: #d4d4d4; height: 100vh; display: flex; flex-direction: column; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; overflow: hidden; }
.header { height: 50px; background: #252526; border-bottom: 1px solid #3e3e42; display: flex; justify-content: space-between; align-items: center; padding: 0 20px; flex-shrink: 0; }
.header-left { display: flex; align-items: center; gap: 10px; }
.logo { font-size: 20px; }
.title { font-size: 15px; color: #cccccc; font-weight: 500; }
.main-layout { display: flex; flex: 1; overflow: hidden; padding: 10px; gap: 10px; }
.panel { background: #252526; border: 1px solid #3e3e42; border-radius: 4px; display: flex; flex-direction: column; }
.panel-title { padding: 8px 15px; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #bbbbbb; border-bottom: 1px solid #3e3e42; background: #2d2d30; font-weight: bold; }
.left-panel { width: 30%; } /* 稍微加宽一点放复选框 */
.case-list { padding: 10px 0; overflow-y: auto; flex: 1; }
.case-item { padding: 10px 15px; display: flex; align-items: center; gap: 10px; font-size: 13px; color: #9cdcfe; border-left: 3px solid transparent; transition: background 0.2s; }
.case-item.active { background: #37373d; border-left-color: #409EFF; }
.case-name { cursor: pointer; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } /* 鼠标变手型，超长省略 */
.case-name:hover { color: #ffffff; } /* 悬停高亮 */
.status-icon { width: 20px; text-align: center; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
.dot.pending { background: #6e7681; }
.dot.running { background: #409EFF; animation: blink 1s infinite; }
.dot.pass { color: #67C23A; font-size: 14px; background: transparent; width: auto; }
.dot.fail { color: #F56C6C; font-size: 14px; background: transparent; width: auto; }
@keyframes blink { 50% { opacity: 0.2; } }
.center-panel { flex: 1; }
.terminal { flex: 1; padding: 15px; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; line-height: 1.6; overflow-y: auto; background: #1e1e1e; }
.terminal-placeholder { color: #6e7681; }
.log-line { white-space: pre-wrap; word-break: break-all; }
.right-panel { width: 20%; }
.data-cards { padding: 10px; display: flex; flex-direction: column; gap: 10px; }
.data-card { background: #2d2d30; padding: 12px; border-radius: 4px; border-left: 3px solid #3e3e42; }
.data-card.full-width { border-left-color: #67C23A; }
.label { font-size: 11px; color: #8b949e; margin-bottom: 5px; text-transform: uppercase; }
.value { font-size: 20px; font-weight: bold; color: #d2d8de; }
.unit { font-size: 12px; color: #8b949e; margin-left: 4px; font-weight: normal; }
.temp { color: #4fc1ff; }
.pm { color: #e5c07b; }
.co2 { color: #c678dd; }
.normal { color: #67C23A; }
.fault { color: #F56C6C; animation: blink 1s infinite; }

/* 报告弹窗 */
:deep(.report-dialog .el-dialog) { background: #fff; color: #333; border-radius: 8px; }
:deep(.report-dialog .el-dialog__header) { border-bottom: 1px solid #eee; }
:deep(.report-dialog .el-dialog__title) { color: #333; font-weight: bold; }

/* 抽屉组件深色覆盖 (让它融入背景) */
:deep(.el-drawer) { background: #2d2d30 !important; color: #d4d4d4 !important; }
:deep(.el-drawer__header) { color: #ffffff !important; border-bottom: 1px solid #3e3e42; margin-bottom: 0; padding-bottom: 15px;}
:deep(.el-drawer__body) { padding-top: 10px; }
:deep(.el-input__wrapper) { background: #1e1e1e !important; box-shadow: 0 0 0 1px #3e3e42 inset !important; }
:deep(.el-input__inner) { color: #d4d4d4 !important; }
:deep(.el-form-item__label) { color: #bbbbbb !important; }
</style>