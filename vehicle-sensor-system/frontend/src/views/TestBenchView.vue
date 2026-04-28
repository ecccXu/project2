<!-- frontend/src/views/TestBenchView.vue -->
<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  getNodes,
  getBenchCases,
  runBench,
  stopBench,
  getBenchStatus,
  getBenchLogs,
  getBenchReport,
  saveReport,
} from '@/api'

// ==========================================
// 状态：节点
// ==========================================
const availableNodes = ref([])
const benchNode = ref('')

// ==========================================
// 状态：用例
// ==========================================
const caseTemplates = ref([])
const selectedCaseIds = ref([])
const drawerVisible = ref(false)
const editingCase = ref(null)
const editingParams = ref({})

// ==========================================
// 状态：执行
// ==========================================
const benchStatus = ref({
  is_running: false,
  current_case: '等待启动',
  progress: '0/0',
  results_summary: [],
})
const terminalLogs = ref([])
const terminalRef = ref(null)

// ==========================================
// 状态：报告
// ==========================================
const reportVisible = ref(false)
const reportData = ref(null)
const reportChartRef = ref(null)
const reportChartInst = ref(null)

// ==========================================
// 节点列表获取
// ==========================================
const fetchNodes = async () => {
  try {
    const res = await getNodes()
    availableNodes.value = res.nodes || []
    if (availableNodes.value.length > 0 && !benchNode.value) {
      benchNode.value = availableNodes.value[0].node_id
    }
  } catch (e) {
    console.error('获取节点列表失败', e)
  }
}

// ==========================================
// 用例列表获取
// ==========================================
const fetchCases = async () => {
  try {
    const res = await getBenchCases()
    if (res?.cases) {
      caseTemplates.value = res.cases.map(c => ({
        ...c,
        current_params: { ...c.default_params },
      }))
    }
  } catch (e) {
    console.error('获取用例列表失败', e)
  }
}

// ==========================================
// 用例参数编辑
// ==========================================
const handleCaseClick = (caseItem) => {
  editingCase.value = caseItem
  editingParams.value = { ...caseItem.current_params }
  drawerVisible.value = true
}

const saveParams = () => {
  if (editingCase.value) {
    const converted = {}
    for (const [key, val] of Object.entries(editingParams.value)) {
      const num = Number(val)
      converted[key] = (!isNaN(num) && val !== '') ? num : val
    }
    editingCase.value.current_params = converted
  }
  drawerVisible.value = false
}

// ==========================================
// 启动测试
// ==========================================
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
    is_running: true,
    current_case: '系统初始化...',
    progress: '0/0',
    results_summary: [],
  }

  const payload = selectedCaseIds.value.map(caseId => {
    const template = caseTemplates.value.find(c => c.id === caseId)
    return {
      id: caseId,
      params: template ? { ...template.current_params } : {},
    }
  })

  try {
    // 注意：runBench 需要传 node_id 作为 query 参数
    // 由于我们的 API 封装是把 payload 作为 body，这里需要特殊处理
    const res = await runBenchWithNode(benchNode.value, payload)

    if (res.status === 'error') {
      ElMessage.error(`启动失败：${res.message}`)
      benchStatus.value.is_running = false
      return
    }
    ElMessage.success(res.message)
    startPolling()
  } catch (e) {
    ElMessage.error('请求失败，请检查后端是否运行')
    benchStatus.value.is_running = false
  }
}

// 由于 bench/run 接口需要 node_id 作为 query 参数，单独封装
import request from '@/api/request'
const runBenchWithNode = (nodeId, cases) => {
  return request.post(`/api/bench/run?node_id=${nodeId}`, cases)
}

// ==========================================
// 强制停止
// ==========================================
const handleStopBench = async () => {
  try {
    const res = await stopBench()
    ElMessage.warning(res.message)
  } catch (e) {
    ElMessage.error('停止请求失败')
  }
}

// ==========================================
// 轮询状态和日志
// ==========================================
let statusTimer = null

const startPolling = () => {
  stopPolling()
  let errorCount = 0

  statusTimer = setInterval(async () => {
    try {
      const [statusRes, logRes] = await Promise.all([
        getBenchStatus(),
        getBenchLogs(),
      ])
      benchStatus.value = statusRes
      terminalLogs.value = logRes.logs || []
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

// ==========================================
// 获取报告
// ==========================================
const fetchFinalReport = async () => {
  try {
    const res = await getBenchReport()
    if (res.status === 'success') {
      reportData.value = res
      reportVisible.value = true
      await nextTick()
      initReportChart()
    }
  } catch (e) {
    console.error('获取报告失败', e)
  }
}

const handleSaveReport = async () => {
  try {
    const res = await saveReport()
    ElMessage.success(`报告已保存，ID: ${res.report_id}`)
  } catch (e) {
    ElMessage.error('保存失败，请确认测试已结束')
  }
}

const initReportChart = () => {
  if (!reportData.value) return
  const dom = reportChartRef.value
  if (!dom) return
  if (reportChartInst.value) reportChartInst.value.dispose()

  reportChartInst.value = echarts.init(dom)
  reportChartInst.value.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['45%', '75%'],
      itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, fontSize: 14, formatter: '{b}\n{d}%' },
      data: [
        {
          value: reportData.value.pass_count,
          name: '通过',
          itemStyle: { color: '#10B981' },
        },
        {
          value: reportData.value.fail_count,
          name: '失败',
          itemStyle: { color: '#EF4444' },
        },
        {
          value: reportData.value.error_count || 0,
          name: '错误',
          itemStyle: { color: '#F59E0B' },
        },
      ],
    }],
  })
}

// ==========================================
// 用例状态匹配
// ==========================================
const getCaseStatus = (caseId) => {
  const found = benchStatus.value.results_summary.find(
    r => r.case_id === caseId
  )
  if (!found) {
    if (benchStatus.value.current_case?.includes(caseId)) return 'RUNNING'
    return 'PENDING'
  }
  return found.status
}

// ==========================================
// 日志格式化
// ==========================================
const formatLog = (log) => {
  const escaped = log
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  if (escaped.includes('FAIL') || escaped.includes('错误') || escaped.includes('异常'))
    return `<span style="color:#EF4444;">${escaped}</span>`
  if (escaped.includes('PASS') || escaped.includes('成功') || escaped.includes('有效') || escaped.includes('拦截'))
    return `<span style="color:#10B981;">${escaped}</span>`
  if (escaped.includes('-> 下发指令'))
    return `<span style="color:#2563EB;">${escaped}</span>`
  if (escaped.includes('警告') || escaped.includes('INTERRUPTED'))
    return `<span style="color:#F59E0B;">${escaped}</span>`
  return escaped
}

// ==========================================
// 生命周期
// ==========================================
let nodesTimer = null

onMounted(() => {
  fetchNodes()
  fetchCases()
  nodesTimer = setInterval(fetchNodes, 5000)
})

onUnmounted(() => {
  stopPolling()
  if (nodesTimer) clearInterval(nodesTimer)
  if (reportChartInst.value) reportChartInst.value.dispose()
})
</script>

<template>
  <div class="bench-view">

    <div class="bench-layout">

      <!-- ===== 左侧：用例编排 ===== -->
      <div class="bench-left">
        <div class="panel-title">测试用例编排</div>

        <!-- 节点选择 -->
        <div class="panel-section">
          <span class="section-label">目标节点</span>
          <el-select
            v-model="benchNode"
            placeholder="选择节点"
            style="width: 100%"
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
        <div class="panel-section panel-section-flex">
          <span class="section-label">测试用例</span>
          <div class="case-list">
            <div
              v-for="c in caseTemplates"
              :key="c.id"
              class="case-item"
              :class="{ 'is-active': getCaseStatus(c.id) === 'RUNNING' }"
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
                <span v-if="getCaseStatus(c.id) === 'PENDING'" class="dot pending" />
                <span v-else-if="getCaseStatus(c.id) === 'RUNNING'" class="dot running" />
                <span v-else-if="getCaseStatus(c.id) === 'PASS'" class="dot pass">✓</span>
                <span v-else-if="getCaseStatus(c.id) === 'FAIL'" class="dot fail">✕</span>
                <span v-else-if="getCaseStatus(c.id) === 'ERROR'" class="dot error">!</span>
              </span>
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="bench-actions">
          <el-button
            type="primary"
            :loading="benchStatus.is_running"
            :disabled="selectedCaseIds.length === 0 || !benchNode"
            @click="startBench"
            style="width: 100%"
            size="large"
          >
            {{ benchStatus.is_running
                ? '运行中...'
                : `执行选中用例 (${selectedCaseIds.length})` }}
          </el-button>
          <el-button
            type="danger"
            :disabled="!benchStatus.is_running"
            @click="handleStopBench"
            style="width: 100%; margin-top: 8px; margin-left: 0"
            size="large"
          >
            ⏹ 强制停止
          </el-button>
        </div>
      </div>

      <!-- ===== 右侧：执行控制台 ===== -->
      <div class="bench-right">
        <div class="panel-title">
          执行控制台
          <span class="panel-status">
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

    <!-- ===== 参数编辑抽屉 ===== -->
    <el-drawer
      v-model="drawerVisible"
      title="用例参数配置"
      direction="rtl"
      size="360px"
    >
      <div v-if="editingCase" style="padding: 0 8px">
        <h4 class="drawer-title">{{ editingCase.name }}</h4>
        <p class="drawer-hint">
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
            class="drawer-empty"
          >
            该用例无可配置参数
          </div>
        </el-form>
        <el-button
          type="primary"
          style="width: 100%; margin-top: 16px"
          @click="saveParams"
        >
          保存并关闭
        </el-button>
      </div>
    </el-drawer>

    <!-- ===== 测试报告弹窗 ===== -->
    <el-dialog
      v-model="reportVisible"
      title="台架测试分析报告"
      width="80%"
      :close-on-click-modal="false"
    >
      <div v-if="reportData">
        <el-row :gutter="24">
          <el-col :span="8">
            <div ref="reportChartRef" style="height: 260px" />
          </el-col>
          <el-col :span="16">
            <el-descriptions
              :column="3"
              border
              size="small"
              style="margin-bottom: 16px"
            >
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
              max-height="240"
              size="small"
            >
              <el-table-column prop="case" label="用例名称" min-width="160" />
              <el-table-column prop="status" label="结果" width="80">
                <template #default="{ row }">
                  <el-tag
                    :type="row.status === 'PASS' ? 'success' : 'danger'"
                    size="small"
                  >
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="duration" label="耗时(s)" width="90" />
              <el-table-column
                prop="details"
                label="详情"
                show-overflow-tooltip
              >
                <template #default="{ row }">
                  {{ Array.isArray(row.details) ? row.details.join(' | ') : row.details }}
                </template>
              </el-table-column>
            </el-table>
          </el-col>
        </el-row>
      </div>
      <template #footer>
        <el-button type="success" @click="handleSaveReport">
          💾 保存报告
        </el-button>
        <el-button @click="reportVisible = false">关闭</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<style scoped>
.bench-view {
  width: 100%;
  height: 100%;
}

/* 整体布局 */
.bench-layout {
  display: flex;
  gap: var(--spacing-4);
  height: calc(100vh - 140px);
  overflow: hidden;
}

/* 左侧面板 */
.bench-left {
  width: 320px;
  flex-shrink: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

/* 右侧面板 */
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

/* 面板标题 */
.panel-title {
  font-size: var(--font-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  letter-spacing: 0.3px;
  padding: var(--spacing-3) var(--spacing-4);
  background: var(--bg-page);
  border-bottom: 1px solid var(--border-color);
}

.panel-status {
  font-size: var(--font-xs);
  color: var(--text-tertiary);
  margin-left: var(--spacing-3);
  font-weight: var(--font-weight-normal);
}

/* 面板分区 */
.panel-section {
  padding: var(--spacing-4);
  border-bottom: 1px solid var(--border-light);
}

.panel-section-flex {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border-bottom: none;
}

.section-label {
  display: block;
  font-size: var(--font-xs);
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: var(--spacing-2);
  font-weight: var(--font-weight-medium);
}

/* 用例列表 */
.case-list {
  flex: 1;
  overflow-y: auto;
  padding-top: var(--spacing-2);
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

.case-item.is-active {
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

/* 操作按钮区域 */
.bench-actions {
  padding: var(--spacing-4);
  border-top: 1px solid var(--border-light);
}

/* 终端 */
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

/* 抽屉样式 */
.drawer-title {
  color: var(--color-primary);
  margin-bottom: var(--spacing-2);
  font-size: var(--font-md);
  font-weight: var(--font-weight-semibold);
}

.drawer-hint {
  color: var(--text-tertiary);
  font-size: var(--font-xs);
  margin-bottom: var(--spacing-4);
  line-height: 1.5;
}

.drawer-empty {
  color: var(--text-tertiary);
  text-align: center;
  margin-top: var(--spacing-8);
  font-size: var(--font-sm);
}

/* 动画 */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>