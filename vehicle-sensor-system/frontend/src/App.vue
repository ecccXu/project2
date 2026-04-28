<!-- frontend/src/App.vue -->
<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

const API_BASE = 'http://127.0.0.1:8000'

// ==========================================
// 全局状态
// ==========================================
const activeTab       = ref('monitor')   // 当前激活的Tab
const availableNodes  = ref([])          // 在线节点列表
const selectedNode    = ref('')          // 当前选中的节点ID

// ==========================================
// Tab1：实时监控
// ==========================================
const monitorData    = ref({})    // 当前节点最新数据
const isAbnormal     = ref(false) // 是否有告警
const abnormalMsg    = ref('')    // 告警信息
let   monitorTimer   = null

const fetchMonitorData = async () => {
  if (!selectedNode.value) return
  try {
    const res = await axios.get(`${API_BASE}/api/nodes/${selectedNode.value}`)
    monitorData.value = res.data.latest_data || {}
    isAbnormal.value  = monitorData.value.is_abnormal || false
    abnormalMsg.value = monitorData.value.error_msg   || ''
  } catch (e) {
    console.error('监控数据获取失败', e)
  }
}

// ==========================================
// Tab2：测试执行
// ==========================================
// 用例编排
const caseTemplates    = ref([])
const selectedCaseIds  = ref([])
const drawerVisible    = ref(false)
const editingCase      = ref(null)
const editingParams    = ref({})
const benchNode        = ref('')     // 测试目标节点

// 运行状态
const benchStatus = ref({
  is_running:       false,
  current_case:     '等待启动',
  progress:         '0/0',
  results_summary:  [],
})
const terminalLogs     = ref([])
const terminalRef      = ref(null)
const reportVisible    = ref(false)
const reportData       = ref(null)
const reportChartRef   = ref(null)
const reportChartInst  = ref(null)
let   statusTimer      = null

// 用例列表获取
const fetchCases = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/bench/cases`)
    if (res.data?.cases) {
      caseTemplates.value = res.data.cases.map(c => ({
        ...c,
        current_params: { ...c.default_params },
      }))
    }
  } catch (e) {
    console.error('获取用例列表失败', e)
  }
}

// 点击用例名称，打开参数编辑抽屉
const handleCaseClick = (caseItem) => {
  editingCase.value   = caseItem
  editingParams.value = { ...caseItem.current_params }
  drawerVisible.value = true
}

// 保存参数（修复类型丢失问题）
const saveParams = () => {
  if (editingCase.value) {
    const converted = {}
    for (const [key, val] of Object.entries(editingParams.value)) {
      // el-input返回字符串，尝试转为数字
      const num = Number(val)
      converted[key] = (!isNaN(num) && val !== '') ? num : val
    }
    editingCase.value.current_params = converted
  }
  drawerVisible.value = false
}

// 启动测试
const startBench = async () => {
  if (selectedCaseIds.value.length === 0) {
    ElMessage.warning('请至少勾选一个测试用例！')
    return
  }
  if (!benchNode.value) {
    ElMessage.warning('请选择测试目标节点！')
    return
  }

  terminalLogs.value = []
  reportVisible.value = false
  benchStatus.value = {
    is_running:      true,
    current_case:    '系统初始化...',
    progress:        '0/0',
    results_summary: [],
  }

  const payload = selectedCaseIds.value.map(caseId => {
    const template = caseTemplates.value.find(c => c.id === caseId)
    return {
      id:     caseId,
      params: template ? { ...template.current_params } : {},
    }
  })

  try {
    const res = await axios.post(
      `${API_BASE}/api/bench/run?node_id=${benchNode.value}`,
      payload
    )
    if (res.data.status === 'error') {
      ElMessage.error(`启动失败：${res.data.message}`)
      benchStatus.value.is_running = false
      return
    }
    ElMessage.success(res.data.message)
    startPolling()
  } catch (e) {
    ElMessage.error('请求失败，请检查后端是否运行')
    benchStatus.value.is_running = false
  }
}

// 强制停止测试
const stopBench = async () => {
  try {
    const res = await axios.post(`${API_BASE}/api/bench/stop`)
    ElMessage.warning(res.data.message)
  } catch (e) {
    ElMessage.error('停止请求失败')
  }
}

// 轮询状态和日志
const startPolling = () => {
  stopPolling()
  let errorCount = 0
  statusTimer = setInterval(async () => {
    try {
      const [statusRes, logRes] = await Promise.all([
        axios.get(`${API_BASE}/api/bench/status`),
        axios.get(`${API_BASE}/api/bench/logs`),
      ])
      benchStatus.value  = statusRes.data
      terminalLogs.value = logRes.data.logs || []
      errorCount = 0

      await nextTick()
      if (terminalRef.value) {
        terminalRef.value.scrollTop = terminalRef.value.scrollHeight
      }

      // 测试结束自动获取报告
      if (
        !benchStatus.value.is_running &&
        benchStatus.value.results_summary.length > 0
      ) {
        stopPolling()
        fetchFinalReport()
      }
    } catch (e) {
      errorCount++
      if (errorCount > 5) {
        stopPolling()
        ElMessage.error('与后端失去连接，请检查服务是否运行')
      }
    }
  }, 800)
}

const stopPolling = () => {
  if (statusTimer) clearInterval(statusTimer)
  statusTimer = null
}

// 获取测试报告
const fetchFinalReport = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/bench/report`)
    if (res.data.status === 'success') {
      reportData.value    = res.data
      reportVisible.value = true
      await nextTick()
      initReportChart()
    }
  } catch (e) {
    console.error('获取报告失败', e)
  }
}

// 保存报告到数据库
const saveReport = async () => {
  try {
    const res = await axios.post(`${API_BASE}/api/reports/save`)
    ElMessage.success(`报告已保存，ID: ${res.data.report_id}`)
  } catch (e) {
    ElMessage.error('保存失败，请确认测试已结束')
  }
}

// 初始化报告饼图
const initReportChart = () => {
  if (!reportData.value) return
  const dom = reportChartRef.value
  if (!dom) return
  if (reportChartInst.value) reportChartInst.value.dispose()
  reportChartInst.value = echarts.init(dom)
  reportChartInst.value.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type:      'pie',
      radius:    ['40%', '70%'],
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: {
        show:      true,
        fontSize:  14,
        formatter: '{b}\n{d}%',
      },
      data: [
        {
          value:     reportData.value.pass_count,
          name:      '通过',
          itemStyle: { color: '#67C23A' },
        },
        {
          value:     reportData.value.fail_count,
          name:      '失败',
          itemStyle: { color: '#F56C6C' },
        },
        {
          value:     reportData.value.error_count || 0,
          name:      '错误',
          itemStyle: { color: '#E6A23C' },
        },
      ],
    }],
  })
}

// 用例状态（精确匹配case_id，修复旧版模糊匹配问题）
const getCaseStatus = (caseId) => {
  const found = benchStatus.value.results_summary.find(
    r => r.case_id === caseId   // ✅ 精确匹配
  )
  if (!found) {
    if (benchStatus.value.current_case?.includes(caseId)) return 'RUNNING'
    return 'PENDING'
  }
  return found.status
}

// 日志格式化（移入script setup，解决混用API问题）
const formatLog = (log) => {
  // 先转义HTML，防止XSS
  const escaped = log
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  if (escaped.includes('FAIL') || escaped.includes('错误') || escaped.includes('异常'))
    return `<span style="color:#F56C6C;">${escaped}</span>`
  if (escaped.includes('PASS') || escaped.includes('成功') || escaped.includes('有效') || escaped.includes('拦截'))
    return `<span style="color:#67C23A;">${escaped}</span>`
  if (escaped.includes('-> 下发指令'))
    return `<span style="color:#409EFF;">${escaped}</span>`
  if (escaped.includes('警告') || escaped.includes('INTERRUPTED'))
    return `<span style="color:#E6A23C;">${escaped}</span>`
  return escaped
}

// ==========================================
// Tab3：历史数据
// ==========================================
const historyNode      = ref('')
const historyAbnormal  = ref(null)     // null=全部 true=仅异常
const historyData      = ref([])
const historyTotal     = ref(0)
const historyPage      = ref(1)
const historyPageSize  = ref(20)
const historyLoading   = ref(false)

const fetchHistory = async () => {
  historyLoading.value = true
  try {
    const params = {
      limit:  historyPageSize.value,
      offset: (historyPage.value - 1) * historyPageSize.value,
    }
    if (historyNode.value)           params.node_id     = historyNode.value
    if (historyAbnormal.value !== null) params.is_abnormal = historyAbnormal.value

    const res     = await axios.get(`${API_BASE}/api/data/history`, { params })
    historyData.value  = res.data.data  || []
    historyTotal.value = res.data.total || 0
  } catch (e) {
    ElMessage.error('历史数据获取失败')
  } finally {
    historyLoading.value = false
  }
}

const handleHistoryPageChange = (page) => {
  historyPage.value = page
  fetchHistory()
}

const resetHistory = () => {
  historyNode.value     = ''
  historyAbnormal.value = null
  historyPage.value     = 1
  fetchHistory()
}

// ==========================================
// Tab4：历史报告
// ==========================================
const reportListNode     = ref('')
const reportList         = ref([])
const reportListTotal    = ref(0)
const reportListPage     = ref(1)
const reportListLoading  = ref(false)
const detailVisible      = ref(false)
const detailReport       = ref(null)
const detailChartRef     = ref(null)
const detailChartInst    = ref(null)

const fetchReportList = async () => {
  reportListLoading.value = true
  try {
    const params = {
      limit:  10,
      offset: (reportListPage.value - 1) * 10,
    }
    if (reportListNode.value) params.node_id = reportListNode.value

    const res          = await axios.get(`${API_BASE}/api/reports/list`, { params })
    reportList.value      = res.data.reports || []
    reportListTotal.value = res.data.total   || 0
  } catch (e) {
    ElMessage.error('报告列表获取失败')
  } finally {
    reportListLoading.value = false
  }
}

const viewReportDetail = async (reportId) => {
  try {
    const res        = await axios.get(`${API_BASE}/api/reports/${reportId}`)
    detailReport.value  = res.data.report
    detailVisible.value = true
    await nextTick()
    initDetailChart()
  } catch (e) {
    ElMessage.error('报告详情获取失败')
  }
}

const initDetailChart = () => {
  if (!detailReport.value) return
  const dom = detailChartRef.value
  if (!dom) return
  if (detailChartInst.value) detailChartInst.value.dispose()
  detailChartInst.value = echarts.init(dom)
  detailChartInst.value.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type:      'pie',
      radius:    ['40%', '70%'],
      itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, fontSize: 13, formatter: '{b}\n{d}%' },
      data: [
        {
          value:     detailReport.value.pass_count,
          name:      '通过',
          itemStyle: { color: '#67C23A' },
        },
        {
          value:     detailReport.value.fail_count,
          name:      '失败',
          itemStyle: { color: '#F56C6C' },
        },
        {
          value:     detailReport.value.error_count || 0,
          name:      '错误',
          itemStyle: { color: '#E6A23C' },
        },
      ],
    }],
  })
}

// ==========================================
// 全局：获取在线节点列表
// ==========================================
const fetchNodes = async () => {
  try {
    const res       = await axios.get(`${API_BASE}/api/nodes`)
    availableNodes.value = res.data.nodes || []
    // 默认选中第一个节点
    if (availableNodes.value.length > 0 && !selectedNode.value) {
      selectedNode.value = availableNodes.value[0].node_id
      benchNode.value    = availableNodes.value[0].node_id
    }
  } catch (e) {
    console.error('获取节点列表失败', e)
  }
}

// Tab切换时刷新对应数据
const handleTabChange = (tabName) => {
  if (tabName === 'history') {
    fetchHistory()
  } else if (tabName === 'reports') {
    fetchReportList()
  }
}

// ==========================================
// 生命周期
// ==========================================
let nodesTimer   = null
let monitorTimer2 = null

onMounted(() => {
  fetchCases()
  fetchNodes()

  // 定期刷新节点列表（ESP32接入后自动出现）
  nodesTimer = setInterval(fetchNodes, 5000)

  // 定期刷新监控数据
  monitorTimer2 = setInterval(fetchMonitorData, 1500)
})

onUnmounted(() => {
  stopPolling()
  if (nodesTimer)    clearInterval(nodesTimer)
  if (monitorTimer2) clearInterval(monitorTimer2)
  if (reportChartInst.value) reportChartInst.value.dispose()
  if (detailChartInst.value) detailChartInst.value.dispose()
})
</script>

<template>
  <div class="app-container">
    <!-- ==================== Header ==================== -->
    <div class="header">
      <div class="header-left">
        <span class="logo">⚡</span>
        <span class="title">车载环境传感器 | 自动化台架测试系统</span>
      </div>
      <div class="header-right">
        <span class="node-count">
          在线节点：{{ availableNodes.length }} 个
        </span>
      </div>
    </div>

    <!-- ==================== Tabs ==================== -->
    <el-tabs
      v-model="activeTab"
      type="border-card"
      class="main-tabs"
      @tab-change="handleTabChange"
    >

      <!-- ========== Tab1：实时监控 ========== -->
      <el-tab-pane label="📡 实时监控" name="monitor">
        <div class="tab-content">
          <!-- 节点选择 -->
          <div class="toolbar">
            <span class="toolbar-label">监控节点：</span>
            <el-select
              v-model="selectedNode"
              placeholder="请选择节点"
              style="width:200px"
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
              style="margin-left:10px"
            >
              暂无在线节点，请启动模拟器或接入ESP32
            </el-tag>
          </div>

          <!-- 告警横幅 -->
          <el-alert
            v-if="isAbnormal"
            :title="`⚠️ 数据异常告警：${abnormalMsg}`"
            type="error"
            :closable="false"
            style="margin-bottom:16px"
          />

          <!-- 数据卡片 -->
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
              <div class="card-label">CO2浓度</div>
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
                <div style="font-size:11px;color:#8b949e;margin-top:4px">
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
      </el-tab-pane>

      <!-- ========== Tab2：测试执行 ========== -->
      <el-tab-pane label="🧪 测试执行" name="bench">
        <div class="tab-content bench-layout">

          <!-- 左侧：用例编排 -->
          <div class="bench-left">
            <div class="panel-title">测试用例编排</div>

            <!-- 节点选择 -->
            <div class="bench-node-select">
              <span class="toolbar-label">目标节点：</span>
              <el-select
                v-model="benchNode"
                placeholder="选择节点"
                style="width:160px"
                :disabled="benchStatus.is_running"
              >
                <el-option
                  v-for="n in availableNodes"
                  :key="n.node_id"
                  :label="n.node_id"
                  :value="n.node_id"
                />
              </el-select>
            </div>

            <!-- 用例列表 -->
            <div class="case-list">
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
                />
                <span
                  class="case-name"
                  @click="handleCaseClick(c)"
                  title="点击编辑参数"
                >
                  {{ c.name }}
                </span>
                <span class="status-icon">
                  <span v-if="getCaseStatus(c.id) === 'PENDING'"      class="dot pending" />
                  <span v-else-if="getCaseStatus(c.id) === 'RUNNING'" class="dot running" />
                  <span v-else-if="getCaseStatus(c.id) === 'PASS'"    class="dot pass">✓</span>
                  <span v-else-if="getCaseStatus(c.id) === 'FAIL'"    class="dot fail">✕</span>
                  <span v-else-if="getCaseStatus(c.id) === 'ERROR'"   class="dot error">!</span>
                </span>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="bench-actions">
              <el-button
                type="primary"
                :loading="benchStatus.is_running"
                :disabled="selectedCaseIds.length === 0 || !benchNode"
                @click="startBench"
                style="width:100%"
              >
                {{ benchStatus.is_running
                    ? '运行中...'
                    : `执行选中用例 (${selectedCaseIds.length})` }}
              </el-button>
              <el-button
                type="danger"
                :disabled="!benchStatus.is_running"
                @click="stopBench"
                style="width:100%;margin-top:8px;margin-left:0"
              >
                ⏹ 强制停止
              </el-button>
            </div>
          </div>

          <!-- 右侧：执行控制台 -->
          <div class="bench-right">
            <div class="panel-title">
              执行控制台
              <span style="font-size:12px;color:#8b949e;margin-left:10px">
                进度：{{ benchStatus.progress }}
                | 当前：{{ benchStatus.current_case }}
                | 节点：{{ benchStatus.target_node || '--' }}
              </span>
            </div>
            <div ref="terminalRef" class="terminal">
              <div
                v-if="terminalLogs.length === 0"
                class="terminal-placeholder"
              >
                > 勾选用例并选择节点，点击"执行选中用例"开始测试...
              </div>
              <div
                v-for="(log, idx) in terminalLogs"
                :key="idx"
                class="log-line"
                v-html="formatLog(log)"
              />
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ========== Tab3：历史数据 ========== -->
      <el-tab-pane label="📊 历史数据" name="history">
        <div class="tab-content">
          <!-- 筛选工具栏 -->
          <div class="toolbar">
            <span class="toolbar-label">节点筛选：</span>
            <el-select
              v-model="historyNode"
              placeholder="全部节点"
              clearable
              style="width:160px;margin-right:12px"
            >
              <el-option
                v-for="n in availableNodes"
                :key="n.node_id"
                :label="n.node_id"
                :value="n.node_id"
              />
            </el-select>

            <span class="toolbar-label">数据状态：</span>
            <el-select
              v-model="historyAbnormal"
              placeholder="全部"
              clearable
              style="width:120px;margin-right:12px"
            >
              <el-option label="全部"   :value="null"  />
              <el-option label="仅异常" :value="true"  />
              <el-option label="仅正常" :value="false" />
            </el-select>

            <el-button type="primary" @click="fetchHistory">查询</el-button>
            <el-button @click="resetHistory">重置</el-button>
          </div>

          <!-- 数据表格 -->
          <el-table
            :data="historyData"
            v-loading="historyLoading"
            stripe
            border
            style="width:100%"
            :row-class-name="({row}) => row.is_abnormal ? 'abnormal-row' : ''"
          >
            <el-table-column prop="sensor_id"   label="节点ID"   width="140" />
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
            <el-table-column prop="co2" label="CO2(ppm)" width="100">
              <template #default="{ row }">
                {{ row.co2?.toFixed(1) ?? '--' }}
              </template>
            </el-table-column>
            <el-table-column prop="status"     label="状态"   width="90">
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
            <el-table-column prop="latency_ms"  label="延迟(ms)" width="90" />
            <el-table-column prop="server_time" label="采集时间"  width="160" />
          </el-table>

          <!-- 分页 -->
          <div class="pagination">
            <el-pagination
              v-model:current-page="historyPage"
              :page-size="historyPageSize"
              :total="historyTotal"
              layout="total, prev, pager, next"
              @current-change="handleHistoryPageChange"
            />
          </div>
        </div>
      </el-tab-pane>

      <!-- ========== Tab4：历史报告 ========== -->
      <el-tab-pane label="📋 历史报告" name="reports">
        <div class="tab-content">
          <!-- 筛选工具栏 -->
          <div class="toolbar">
            <span class="toolbar-label">节点筛选：</span>
            <el-select
              v-model="reportListNode"
              placeholder="全部节点"
              clearable
              style="width:160px;margin-right:12px"
            >
              <el-option
                v-for="n in availableNodes"
                :key="n.node_id"
                :label="n.node_id"
                :value="n.node_id"
              />
            </el-select>
            <el-button type="primary" @click="fetchReportList">查询</el-button>
          </div>

          <!-- 报告列表 -->
          <el-table
            :data="reportList"
            v-loading="reportListLoading"
            stripe
            border
            style="width:100%"
          >
            <el-table-column prop="id"          label="ID"     width="60"  />
            <el-table-column prop="report_name" label="报告名称"            />
            <el-table-column prop="node_id"     label="节点"   width="140" />
            <el-table-column prop="total_cases" label="总用例" width="80"  />
            <el-table-column prop="pass_count"  label="通过"   width="70">
              <template #default="{ row }">
                <span style="color:#67C23A;font-weight:bold">{{ row.pass_count }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="fail_count"  label="失败"   width="70">
              <template #default="{ row }">
                <span style="color:#F56C6C;font-weight:bold">{{ row.fail_count }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="pass_rate"   label="通过率" width="90">
              <template #default="{ row }">
                <el-tag
                  :type="row.pass_rate >= 80 ? 'success' : 'danger'"
                  size="small"
                >
                  {{ row.pass_rate }}%
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="create_time" label="创建时间" width="160" />
            <el-table-column label="操作" width="90">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  size="small"
                  @click="viewReportDetail(row.id)"
                >
                  查看
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页 -->
          <div class="pagination">
            <el-pagination
              v-model:current-page="reportListPage"
              :page-size="10"
              :total="reportListTotal"
              layout="total, prev, pager, next"
              @current-change="(p) => { reportListPage = p; fetchReportList() }"
            />
          </div>
        </div>
      </el-tab-pane>

    </el-tabs>

    <!-- ========== 参数编辑抽屉 ========== -->
    <el-drawer
      v-model="drawerVisible"
      title="用例参数配置"
      direction="rtl"
      size="320px"
    >
      <div v-if="editingCase" style="padding:0 10px">
        <h4 style="color:#409EFF;margin-bottom:8px">{{ editingCase.name }}</h4>
        <p style="color:#8b949e;font-size:12px;margin-bottom:16px">
          修改参数将覆盖默认值，仅影响本次执行
        </p>
        <el-form label-position="top">
          <el-form-item
            v-for="(value, key) in editingParams"
            :key="key"
            :label="key"
          >
            <el-input
              v-model="editingParams[key]"
              type="number"
              placeholder="请输入数值"
            />
          </el-form-item>
          <div
            v-if="Object.keys(editingParams).length === 0"
            style="color:#6e7681;text-align:center;margin-top:30px"
          >
            该用例无可配置参数
          </div>
        </el-form>
        <el-button
          type="primary"
          style="width:100%;margin-top:16px"
          @click="saveParams"
        >
          保存并关闭
        </el-button>
      </div>
    </el-drawer>

    <!-- ========== 测试报告弹窗 ========== -->
    <el-dialog
      v-model="reportVisible"
      title="台架测试分析报告"
      width="75%"
      :close-on-click-modal="false"
    >
      <div v-if="reportData">
        <el-row :gutter="20">
          <el-col :span="8">
            <div ref="reportChartRef" style="height:250px" />
          </el-col>
          <el-col :span="16">
            <el-descriptions :column="3" border size="small" style="margin-bottom:12px">
              <el-descriptions-item label="目标节点">
                {{ reportData.target_node }}
              </el-descriptions-item>
              <el-descriptions-item label="总用例">
                {{ reportData.total }}
              </el-descriptions-item>
              <el-descriptions-item label="通过率">
                {{ reportData.pass_rate }}%
              </el-descriptions-item>
            </el-descriptions>
            <el-table
              :data="reportData.details"
              stripe
              border
              max-height="220"
              size="small"
            >
              <el-table-column prop="case"     label="用例名称" min-width="160" />
              <el-table-column prop="status"   label="结果"     width="80">
                <template #default="{ row }">
                  <el-tag
                    :type="row.status === 'PASS' ? 'success' : 'danger'"
                    size="small"
                  >
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="duration" label="耗时(s)"  width="80" />
              <el-table-column prop="details"  label="详情"     show-overflow-tooltip>
                <template #default="{ row }">
                  {{ Array.isArray(row.details) ? row.details.join(' | ') : row.details }}
                </template>
              </el-table-column>
            </el-table>
          </el-col>
        </el-row>
      </div>
      <template #footer>
        <el-button type="success" @click="saveReport">💾 保存报告</el-button>
        <el-button @click="reportVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- ========== 历史报告详情弹窗 ========== -->
    <el-dialog
      v-model="detailVisible"
      :title="`报告详情：${detailReport?.report_name}`"
      width="75%"
    >
      <div v-if="detailReport">
        <el-row :gutter="20">
          <el-col :span="8">
            <div ref="detailChartRef" style="height:220px" />
          </el-col>
          <el-col :span="16">
            <el-descriptions :column="3" border size="small" style="margin-bottom:12px">
              <el-descriptions-item label="节点">
                {{ detailReport.node_id }}
              </el-descriptions-item>
              <el-descriptions-item label="通过率">
                {{ detailReport.pass_rate }}%
              </el-descriptions-item>
              <el-descriptions-item label="创建时间">
                {{ detailReport.create_time }}
              </el-descriptions-item>
            </el-descriptions>
            <el-table
              :data="detailReport.details"
              stripe
              border
              max-height="200"
              size="small"
            >
              <el-table-column prop="case"     label="用例名称" min-width="160" />
              <el-table-column prop="status"   label="结果"     width="80">
                <template #default="{ row }">
                  <el-tag
                    :type="row.status === 'PASS' ? 'success' : 'danger'"
                    size="small"
                  >
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="duration" label="耗时(s)"  width="80" />
              <el-table-column prop="details"  label="详情"     show-overflow-tooltip>
                <template #default="{ row }">
                  {{ Array.isArray(row.details) ? row.details.join(' | ') : row.details }}
                </template>
              </el-table-column>
            </el-table>
          </el-col>
        </el-row>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<style scoped>
/* ==================== 全局布局 ==================== */
.app-container {
  background: var(--bg-page);
  color: var(--text-primary);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: var(--font-family);
}

/* ==================== Header ==================== */
.header {
  height: var(--header-height);
  background: var(--bg-header);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 var(--spacing-6);
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.logo {
  font-size: 24px;
  color: var(--color-primary);
}

.title {
  font-size: var(--font-md);
  color: var(--text-primary);
  font-weight: var(--font-weight-semibold);
  letter-spacing: 0.3px;
}

.node-count {
  font-size: var(--font-sm);
  color: var(--text-tertiary);
  padding: 4px 12px;
  background: var(--color-primary-lighter);
  color: var(--color-primary);
  border-radius: var(--radius-full);
  font-weight: var(--font-weight-medium);
}

/* ==================== Tabs ==================== */
.main-tabs {
  flex: 1;
  margin: var(--spacing-4);
  background: transparent;
  border: none !important;
  box-shadow: none;
}

:deep(.el-tabs--border-card) {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

:deep(.el-tabs--border-card > .el-tabs__header) {
  background: var(--bg-page);
  border-color: var(--border-color);
}

:deep(.el-tabs--border-card > .el-tabs__header .el-tabs__item) {
  color: var(--text-secondary);
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-fast);
  border-color: transparent;
}

:deep(.el-tabs--border-card > .el-tabs__header .el-tabs__item:hover) {
  color: var(--color-primary);
  background: var(--bg-hover);
}

:deep(.el-tabs--border-card > .el-tabs__header .el-tabs__item.is-active) {
  color: var(--color-primary);
  background: var(--bg-card);
  border-bottom: 2px solid var(--color-primary);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-tabs__content) {
  padding: 0;
}

/* ==================== Tab 内容区 ==================== */
.tab-content {
  padding: var(--spacing-6);
  height: calc(100vh - 140px);
  overflow-y: auto;
}

/* ==================== 工具栏 ==================== */
.toolbar {
  display: flex;
  align-items: center;
  margin-bottom: var(--spacing-5);
  flex-wrap: wrap;
  gap: var(--spacing-3);
  padding: var(--spacing-4);
  background: var(--bg-page);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.toolbar-label {
  color: var(--text-secondary);
  font-size: var(--font-sm);
  font-weight: var(--font-weight-medium);
}

/* ==================== 监控数据卡片 ==================== */
.data-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
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

.unit {
  font-size: var(--font-sm);
  color: var(--text-tertiary);
  margin-left: var(--spacing-1);
  font-weight: var(--font-weight-normal);
}

/* 数据卡片不同类别的色彩区分 */
.temp { color: #0EA5E9; }   /* 温度 - 天蓝 */
.hum { color: #06B6D4; }    /* 湿度 - 青色 */
.pm { color: #F59E0B; }     /* PM2.5 - 橙色 */
.co2 { color: #8B5CF6; }    /* CO2 - 紫色 */
.normal { color: var(--color-success); }
.fault {
  color: var(--color-danger);
  animation: pulse 1.5s infinite;
}

/* ==================== 测试执行布局 ==================== */
.bench-layout {
  display: flex;
  gap: var(--spacing-4);
  padding: var(--spacing-6);
  height: calc(100vh - 140px);
  overflow: hidden;
}

.bench-left {
  width: 320px;
  flex-shrink: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  padding: var(--spacing-4);
  gap: var(--spacing-3);
  box-shadow: var(--shadow-sm);
}

.bench-right {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.panel-title {
  font-size: var(--font-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  letter-spacing: 0.3px;
  padding: var(--spacing-3) var(--spacing-4);
  background: var(--bg-page);
  border-bottom: 1px solid var(--border-color);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  margin: calc(var(--spacing-4) * -1) calc(var(--spacing-4) * -1) 0;
}

.bench-right .panel-title {
  margin: 0;
  border-radius: 0;
}

.bench-node-select {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding-top: var(--spacing-2);
}

/* ==================== 用例列表 ==================== */
.case-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-2) 0;
}

.case-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-2);
  font-size: var(--font-sm);
  color: var(--text-primary);
  border-left: 3px solid transparent;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  margin-bottom: 2px;
}

.case-item:hover {
  background: var(--bg-hover);
}

.case-item.active {
  background: var(--color-primary-lighter);
  border-left-color: var(--color-primary);
}

.case-name {
  flex: 1;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-sm);
  color: var(--text-primary);
  transition: color var(--transition-fast);
}

.case-name:hover {
  color: var(--color-primary);
}

.status-icon {
  width: 24px;
  text-align: center;
}

.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.dot.pending { background: var(--text-disabled); }
.dot.running {
  background: var(--color-primary);
  animation: pulse 1.2s infinite;
  box-shadow: 0 0 8px var(--color-primary);
}
.dot.pass {
  color: var(--color-success);
  font-size: var(--font-md);
  background: transparent;
  width: auto;
  font-weight: var(--font-weight-bold);
}
.dot.fail {
  color: var(--color-danger);
  font-size: var(--font-md);
  background: transparent;
  width: auto;
  font-weight: var(--font-weight-bold);
}
.dot.error {
  color: var(--color-warning);
  font-size: var(--font-md);
  background: transparent;
  width: auto;
  font-weight: var(--font-weight-bold);
}

.bench-actions {
  display: flex;
  flex-direction: column;
  padding-top: var(--spacing-2);
  border-top: 1px solid var(--border-light);
}

/* ==================== 终端 ==================== */
.terminal {
  flex: 1;
  padding: var(--spacing-4) var(--spacing-5);
  font-family: var(--font-family-mono);
  font-size: var(--font-sm);
  line-height: 1.7;
  overflow-y: auto;
  background: #FAFBFC;
  color: var(--text-primary);
}

.terminal-placeholder {
  color: var(--text-disabled);
  font-style: italic;
}

.log-line {
  white-space: pre-wrap;
  word-break: break-all;
  padding: 2px 0;
}

/* ==================== 分页 ==================== */
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--spacing-5);
  padding: var(--spacing-3) 0;
}

/* ==================== 表格异常行高亮 ==================== */
:deep(.abnormal-row) {
  background-color: var(--color-danger-bg) !important;
}

:deep(.abnormal-row:hover > td) {
  background-color: var(--color-danger-light) !important;
}

/* ==================== Element Plus 白色主题适配 ==================== */
:deep(.el-drawer) {
  background: var(--bg-card) !important;
  color: var(--text-primary) !important;
}

:deep(.el-drawer__header) {
  color: var(--text-primary) !important;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 0;
  padding-bottom: var(--spacing-4);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-input__wrapper) {
  background: var(--bg-card) !important;
  box-shadow: 0 0 0 1px var(--border-color) inset !important;
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--border-strong) inset !important;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--color-primary) inset !important;
}

:deep(.el-input__inner) {
  color: var(--text-primary) !important;
}

:deep(.el-form-item__label) {
  color: var(--text-secondary) !important;
  font-weight: var(--font-weight-medium);
}

:deep(.el-select__wrapper) {
  background: var(--bg-card) !important;
  box-shadow: 0 0 0 1px var(--border-color) inset !important;
  color: var(--text-primary) !important;
}

:deep(.el-select__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--border-strong) inset !important;
}

:deep(.el-table) {
  background: var(--bg-card);
  color: var(--text-primary);
  border-radius: var(--radius-md);
  overflow: hidden;
}

:deep(.el-table th.el-table__cell) {
  background: var(--bg-page) !important;
  color: var(--text-primary) !important;
  font-weight: var(--font-weight-semibold);
  border-color: var(--border-color) !important;
}

:deep(.el-table tr) {
  background: var(--bg-card) !important;
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background: var(--bg-page) !important;
}

:deep(.el-table td.el-table__cell) {
  border-color: var(--border-light) !important;
  color: var(--text-primary);
}

:deep(.el-table--border .el-table__cell) {
  border-color: var(--border-color) !important;
}

:deep(.el-pagination) {
  color: var(--text-secondary);
  --el-pagination-button-color: var(--text-primary);
  --el-pagination-hover-color: var(--color-primary);
}

:deep(.el-alert--error.is-light) {
  background: var(--color-danger-bg);
  border: 1px solid var(--color-danger-light);
  color: var(--color-danger);
}

:deep(.el-alert--error.is-light .el-alert__title) {
  color: var(--color-danger);
  font-weight: var(--font-weight-medium);
}

:deep(.el-tag) {
  border-radius: var(--radius-sm);
  font-weight: var(--font-weight-medium);
  border: none;
}

:deep(.el-checkbox__label) {
  color: var(--text-primary);
}

:deep(.el-descriptions__label) {
  color: var(--text-secondary) !important;
  font-weight: var(--font-weight-medium);
  background: var(--bg-page) !important;
}

:deep(.el-descriptions__content) {
  color: var(--text-primary) !important;
  background: var(--bg-card) !important;
}

:deep(.el-descriptions__cell) {
  border-color: var(--border-color) !important;
}

:deep(.el-dialog) {
  border-radius: var(--radius-lg);
  overflow: hidden;
}

:deep(.el-dialog__header) {
  background: var(--bg-page);
  margin-right: 0;
  padding: var(--spacing-5) var(--spacing-6);
  border-bottom: 1px solid var(--border-color);
}

:deep(.el-dialog__title) {
  color: var(--text-primary);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-dialog__body) {
  padding: var(--spacing-6);
  color: var(--text-primary);
}

:deep(.el-dialog__footer) {
  border-top: 1px solid var(--border-color);
  padding: var(--spacing-4) var(--spacing-6);
}

/* ==================== 动画 ==================== */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>