<!-- src/App.vue -->
<script setup>
import { Top, Bottom, Delete } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

const API_BASE = 'http://127.0.0.1:8000'

// --- 状态定义 ---
const benchStatus = ref({ is_running: false, current_case: '等待启动', progress: '0/0', results_summary: [] })
const terminalLogs = ref([])
const realtimePool = ref({ latest_data_snapshot: {} })
const reportVisible = ref(false)
const reportData = ref(null)
const reportChartInstance = ref(null)

let statusTimer = null
let poolTimer = null
const terminalRef = ref(null)

// --- 用例编排状态 ---
const caseTemplates = ref([])
const selectedCaseIds = ref([])
const drawerVisible = ref(false)
const editingCase = ref(null)
const editingParams = ref({})

// --- 积木搭建器状态 (新增) ---
const builderVisible = ref(false)
const builderName = ref('新建自定义用例')
const builderSteps = ref([]) // 存放用户编排的步骤数组

// 积木工具箱定义（前端写死的元数据）
const blockToolbox = [
  { category: '动作积木', blocks: [
    { action: 'OVERRIDE_VALUE', name: '强制赋值', params: [{key: 'target', type: 'select', options: ['in_car_temp', 'out_car_temp', 'humidity', 'pm25', 'co2']}, {key: 'value', type: 'number'}] },
    { action: 'SET_SCENARIO', name: '切换工况', params: [{key: 'scenario_name', type: 'select', options: ['static_parking_summer', 'winter_cruising', 'tunnel_following', 'highway_ac_leak']}] },
    { action: 'INJECT_FAULT', name: '注入故障', params: [{key: 'target', type: 'select', options: ['in_car_temp', 'pm25', 'co2']}, {key: 'fault_type', type: 'select', options: ['STUCK', 'OPEN_CIRCUIT', 'SHORT_CIRCUIT']}, {key: 'stuck_value', type: 'number', hidden: true}] },
    { action: 'CLEAR_FAULT', name: '清除故障', params: [] },
    { action: 'WAIT', name: '等待(秒)', params: [{key: 'seconds', type: 'number'}] }
  ]},
  { category: '断言积木', blocks: [
    { action: 'ASSERT_VALUE', name: '数值比对', type: 'assertion', params: [{key: 'target', type: 'select', options: ['in_car_temp', 'out_car_temp', 'humidity', 'pm25', 'co2']}, {key: 'operator', type: 'select', options: ['>', '<', '==', '!=', '>=', '<=']}, {key: 'expected_value', type: 'number'}] },
    { action: 'ASSERT_STATUS', name: '状态判定', type: 'assertion', params: [{key: 'expected_status', type: 'select', options: ['NORMAL', 'FAULT']}] },
    { action: 'ASSERT_FAULT_CODE', name: '故障码判定', type: 'assertion', params: [{key: 'expected_code', type: 'text'}] }
  ]}
]

// --- 核心动作 ---
const startBench = async () => {
  if (selectedCaseIds.value.length === 0) return alert('请至少勾选一个测试用例！')
  terminalLogs.value = []
  benchStatus.value = { is_running: true, current_case: '系统初始化...', progress: '0/0', results_summary: [] }
  reportVisible.value = false
  const payload = selectedCaseIds.value.map(caseId => {
    const template = caseTemplates.value.find(c => c.id === caseId)
    return { id: caseId, params: template ? template.current_params : {} }
  })
  await axios.post(`${API_BASE}/api/bench/run`, payload)
  startPolling()
}

const fetchCases = async () => {
  const res = await axios.get(`${API_BASE}/api/bench/cases`)
  if (res.data && res.data.cases) {
    caseTemplates.value = res.data.cases.map(c => ({ ...c, current_params: { ...c.default_params } }))
  }
}

const handleCaseClick = (caseItem) => {
  editingCase.value = caseItem
  editingParams.value = { ...caseItem.current_params }
  drawerVisible.value = true
}
const saveParams = () => {
  if (editingCase.value) editingCase.value.current_params = { ...editingParams.value }
  drawerVisible.value = false
}

// --- 积木搭建器逻辑 (新增) ---
const openBuilder = () => {
  builderName.value = '新建自定义用例'
  builderSteps.value = []
  builderVisible.value = true
}

const addBlock = (block) => {
  // 深拷贝积木模板，初始化参数值
  const newStep = {
    type: block.type || 'action',
    action: block.action,
    params: {}
  }
  block.params.forEach(p => {
    newStep.params[p.key] = p.type === 'number' ? 0 : (p.options ? p.options[0] : '')
  })
  builderSteps.value.push(newStep)
}

const removeStep = (index) => {
  builderSteps.value.splice(index, 1)
}

const moveStep = (index, direction) => {
  const newIndex = index + direction
  if (newIndex < 0 || newIndex >= builderSteps.value.length) return
  const temp = builderSteps.value[index]
  builderSteps.value[index] = builderSteps.value[newIndex]
  builderSteps.value[newIndex] = temp
  // 触发响应式更新
  builderSteps.value = [...builderSteps.value]
}

const saveBuilderCase = async () => {
  if (builderSteps.value.length === 0) return alert('请至少添加一个积木步骤！')
  try {
    const payload = {
      name: builderName.value,
      steps: builderSteps.value
    }
    const res = await axios.post(`${API_BASE}/api/bench/custom_cases`, payload)
    if (res.data && res.data.id) {
      alert('用例保存成功！已添加到左侧列表。')
      builderVisible.value = false
      fetchCases() // 刷新左侧列表
    }
  } catch (e) {
    alert('保存失败：' + e.response.data.detail)
  }
}

const deleteCustomCase = async (caseId) => {
  try {
    // 弹出二次确认框
    await ElMessageBox.confirm('确定要删除此自定义用例吗？此操作不可恢复。', '警告', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
      customStyle: { backgroundColor: '#2d2d30', borderColor: '#3e3e42', color: '#d4d4d4' }, // 适配暗色主题
      confirmButtonClass: 'el-button--danger'
    })

    // 确认后调用接口
    const res = await axios.delete(`${API_BASE}/api/bench/custom_cases/${caseId}`)
    if (res.data && res.data.status === 'success') {
      ElMessage.success('用例已删除')
      fetchCases() // 刷新左侧列表
    } else {
      ElMessage.error(res.data.message || '删除失败')
    }
  } catch (e) {
    // 用户点了取消，什么都不做
    if (e !== 'cancel') {
      console.error('删除异常', e)
    }
  }
}

// --- 轮询与报告逻辑 ---
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
    series: [{ type: 'pie', radius: ['40%', '70%'], avoidLabelOverlap: false, itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 }, label: { show: true, fontSize: 16, fontWeight: 'bold', formatter: '{b}\n{d}%' }, data: [{ value: reportData.value.pass_count, name: '通过', itemStyle: { color: '#67C23A' } }, { value: reportData.value.fail_count, name: '失败', itemStyle: { color: '#F56C6C' } }] }]
  })
}

const getCaseStatus = (caseId) => {
  const found = benchStatus.value.results_summary.find(r => r.case.includes(caseId))
  if (!found) {
    if (benchStatus.value.current_case.includes(caseId)) return 'RUNNING'
    return 'PENDING'
  }
  return found.status
}

onMounted(() => {
  fetchCases()
  fetchPoolData()
  poolTimer = setInterval(fetchPoolData, 1500)
})
onUnmounted(() => {
  stopPolling()
  if (poolTimer) clearInterval(poolTimer)
  if (reportChartInstance.value) reportChartInstance.value.dispose()
})
// --- 辅助函数 (从 methods 迁移至此以解决渲染问题) ---
const getBlockParams = (action) => {
  for (const cat of blockToolbox) {
    for (const block of cat.blocks) {
      if (block.action === action) return block.params
    }
  }
  return []
}

const formatLog = (log) => {
  if (log.includes('FAIL') || log.includes('错误') || log.includes('异常')) return `<span style="color: #F56C6C;">${log}</span>`
  if (log.includes('PASS') || log.includes('成功') || log.includes('有效')) return `<span style="color: #67C23A;">${log}</span>`
  if (log.includes('-> 下发指令')) return `<span style="color: #409EFF;">${log}</span>`
  if (log.includes('[步骤')) return `<span style="color: #e5c07b;">${log}</span>`
  return log
}
</script>

<template>
  <div class="bench-container">
    <div class="header">
      <div class="header-left">
        <span class="logo">⚡</span>
        <span class="title">车载环境传感器 | 自动化台架测试系统 v2.0</span>
      </div>
      <div class="header-right">
        <el-button type="primary" size="large" @click="startBench" :loading="benchStatus.is_running" :disabled="selectedCaseIds.length === 0">
          {{ benchStatus.is_running ? '台架运行中...' : `执行选中用例 (${selectedCaseIds.length})` }}
        </el-button>
      </div>
    </div>

    <div class="main-layout">
      <!-- 左侧面板 -->
      <div class="panel left-panel">
        <div class="panel-title">测试用例编排</div>
        <div class="case-list">
          <div v-for="c in caseTemplates" :key="c.id" class="case-item" :class="{ active: getCaseStatus(c.id) === 'RUNNING' }">
            <el-checkbox v-model="selectedCaseIds" :label="c.id" :disabled="benchStatus.is_running" style="margin-right: 10px;" />
            <span class="case-name" :title="c.type === 'custom' ? '自定义用例 (点击查看)' : '预置用例 (点击修改参数)'" @click="handleCaseClick(c)">
              {{ c.name }}
              <el-tag v-if="c.type === 'custom'" size="small" type="warning" style="margin-left: 5px;">Custom</el-tag>
            </span>
            <div style="display: flex; align-items: center; margin-left: auto;">
              <!-- 删除按钮：仅对自定义用例且非运行状态时显示 -->
              <el-button
                v-if="c.type === 'custom' && !benchStatus.is_running"
                type="danger"
                :icon="Delete"
                size="small"
                circle
                style="margin-right: 8px;"
                @click.stop="deleteCustomCase(c.id)"
              />
              <!-- 原有的状态指示灯 -->
              <span class="status-icon">
                <span v-if="getCaseStatus(c.id) === 'PENDING'" class="dot pending"></span>
                <span v-else-if="getCaseStatus(c.id) === 'RUNNING'" class="dot running"></span>
                <span v-else-if="getCaseStatus(c.id) === 'PASS'" class="dot pass">✓</span>
                <span v-else class="dot fail">✕</span>
              </span>
            </div>
          </div>
        </div>
        <!-- 新增：底部创建按钮 -->
        <div style="padding: 10px; border-top: 1px solid #3e3e42;">
          <el-button type="warning" size="small" @click="openBuilder" :disabled="benchStatus.is_running" style="width: 100%;">+ 创建自定义用例</el-button>
        </div>
      </div>

      <!-- 中间终端 -->
      <div class="panel center-panel">
        <div class="panel-title">执行控制台</div>
        <div ref="terminalRef" class="terminal">
          <div v-if="terminalLogs.length === 0" class="terminal-placeholder">> 等待启动...</div>
          <div v-for="(log, index) in terminalLogs" :key="index" class="log-line" v-html="formatLog(log)"></div>
        </div>
      </div>

      <!-- 右侧数据 -->
      <div class="panel right-panel">
        <div class="panel-title">数据旁路监控</div>
        <div class="data-cards">
          <div class="data-card"><div class="label">车内温度</div><div class="value temp">{{ realtimePool.latest_data_snapshot?.in_car_temp?.toFixed(1) || '0.0' }}<span class="unit">℃</span></div></div>
          <div class="data-card"><div class="label">PM2.5</div><div class="value pm">{{ realtimePool.latest_data_snapshot?.pm25?.toFixed(1) || '0.0' }}<span class="unit">ug/m³</span></div></div>
          <div class="data-card"><div class="label">CO2</div><div class="value co2">{{ realtimePool.latest_data_snapshot?.co2?.toFixed(1) || '0.0' }}<span class="unit">ppm</span></div></div>
          <div class="data-card full-width"><div class="label">硬件状态</div><div class="value" :class="realtimePool.latest_data_snapshot?.status === 'FAULT' ? 'fault' : 'normal'">{{ realtimePool.latest_data_snapshot?.status || 'NORMAL' }}</div></div>
        </div>
      </div>
    </div>

    <!-- 参数抽屉 -->
    <el-drawer v-model="drawerVisible" title="用例参数配置" direction="rtl" size="300px">
      <div v-if="editingCase" style="padding: 0 10px;">
        <h4 style="color: #409EFF; margin-bottom: 20px;">{{ editingCase.name }}</h4>
        <p style="color: #8b949e; font-size: 12px; margin-bottom: 20px;">修改以下参数将覆盖默认值。</p>
        <el-form label-position="top" size="default">
          <el-form-item v-for="(value, key) in editingParams" :key="key" :label="key">
            <el-input v-model="editingParams[key]" type="number" placeholder="请输入数值" v-if="typeof value === 'number'"></el-input>
            <el-input v-model="editingParams[key]" v-else></el-input>
          </el-form-item>
          <div v-if="Object.keys(editingParams).length === 0" style="color: #6e7681; text-align: center; margin-top: 30px;">该用例无可配置参数</div>
        </el-form>
        <el-button type="primary" @click="saveParams" style="width: 100%; margin-top: 20px;">保存并关闭</el-button>
      </div>
    </el-drawer>

    <!-- 新增：积木搭建器 Dialog -->
    <el-dialog v-model="builderVisible" title="积木式用例搭建器" width="80%" top="5vh" :close-on-click-modal="false" class="builder-dialog">
      <div class="builder-container">
        <el-input v-model="builderName" placeholder="输入用例名称" style="margin-bottom: 15px; max-width: 300px;"></el-input>
        <el-row :gutter="20">
          <!-- 左侧工具箱 -->
          <el-col :span="6">
            <div class="toolbox-panel">
              <div v-for="cat in blockToolbox" :key="cat.category" class="toolbox-group">
                <div class="toolbox-title">{{ cat.category }}</div>
                <el-button v-for="block in cat.blocks" :key="block.action" size="small" style="width: 100%; margin-bottom: 5px; justify-content: flex-start;" @click="addBlock(block)">
                  + {{ block.name }}
                </el-button>
              </div>
            </div>
          </el-col>
          <!-- 右侧画布 -->
          <el-col :span="18">
            <div class="canvas-panel">
              <div v-if="builderSteps.length === 0" class="canvas-placeholder">
                点击左侧积木添加到此画布
              </div>
              <div v-for="(step, index) in builderSteps" :key="index" class="step-card" :class="{ 'assertion-card': step.type === 'assertion' }">
                <div class="step-header">
                  <span class="step-index"># {{ index + 1 }}</span>
                  <el-tag :type="step.type === 'assertion' ? 'danger' : 'info'" size="small">{{ step.action }}</el-tag>
                  <div class="step-actions">
                    <el-button size="small" circle @click="moveStep(index, -1)" :disabled="index === 0"><el-icon><Top /></el-icon></el-button>
                    <el-button size="small" circle @click="moveStep(index, 1)" :disabled="index === builderSteps.length - 1"><el-icon><Bottom /></el-icon></el-button>
                    <el-button size="small" type="danger" circle @click="removeStep(index)"><el-icon><Delete /></el-icon></el-button>
                  </div>
                </div>
                <div class="step-params">
                  <!-- 动态表单渲染 -->
                  <template v-for="param in getBlockParams(step.action)" :key="param.key">
                    <el-form-item label-width="80px" style="margin-bottom: 5px;">
                      <template #label><span style="color: #aaa; font-size: 12px;">{{ param.key }}</span></template>
                      <el-select v-if="param.type === 'select'" v-model="step.params[param.key]" size="small" style="width: 100%;">
                        <el-option v-for="opt in param.options" :key="opt" :label="opt" :value="opt" />
                      </el-select>
                      <el-input v-else-if="param.type === 'number'" v-model.number="step.params[param.key]" size="small" placeholder="数值" />
                      <el-input v-else v-model="step.params[param.key]" size="small" placeholder="文本" />
                    </el-form-item>
                  </template>
                </div>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>
      <template #footer>
        <el-button @click="builderVisible = false">取消</el-button>
        <el-button type="warning" @click="saveBuilderCase">保存为自定义用例</el-button>
      </template>
    </el-dialog>

    <!-- 报告弹窗 -->
    <el-dialog v-model="reportVisible" title="台架深度测试分析报告" width="70%" :close-on-click-modal="false" class="report-dialog">
      <div v-if="reportData" class="report-container">
        <el-row :gutter="20">
          <el-col :span="8"><div id="reportPieChart" style="height: 250px;"></div></el-col>
          <el-col :span="16">
            <el-table :data="reportData.details" stripe border style="width: 100%" max-height="250">
              <el-table-column prop="case" label="用例名称" width="220" />
              <el-table-column prop="status" label="结果" width="80"><template #default="scope"><el-tag :type="scope.row.status === 'PASS' ? 'success' : 'danger'" size="small">{{ scope.row.status }}</el-tag></template></el-table-column>
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

<style scoped>
/* 原有暗黑风格保持不变 */
.bench-container { background: #1e1e1e; color: #d4d4d4; height: 100vh; display: flex; flex-direction: column; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; overflow: hidden; }
.header { height: 50px; background: #252526; border-bottom: 1px solid #3e3e42; display: flex; justify-content: space-between; align-items: center; padding: 0 20px; flex-shrink: 0; }
.header-left { display: flex; align-items: center; gap: 10px; }
.logo { font-size: 20px; }
.title { font-size: 15px; color: #cccccc; font-weight: 500; }
.main-layout { display: flex; flex: 1; overflow: hidden; padding: 10px; gap: 10px; }
.panel { background: #252526; border: 1px solid #3e3e42; border-radius: 4px; display: flex; flex-direction: column; }
.panel-title { padding: 8px 15px; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #bbbbbb; border-bottom: 1px solid #3e3e42; background: #2d2d30; font-weight: bold; }
.left-panel { width: 30%; }
.case-list { padding: 10px 0; overflow-y: auto; flex: 1; }
.case-item { padding: 10px 15px; display: flex; align-items: center; gap: 10px; font-size: 13px; color: #9cdcfe; border-left: 3px solid transparent; transition: background 0.2s; }
.case-item.active { background: #37373d; border-left-color: #409EFF; }
.case-name { cursor: pointer; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.case-name:hover { color: #ffffff; }
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
.temp { color: #4fc1ff; } .pm { color: #e5c07b; } .co2 { color: #c678dd; } .normal { color: #67C23A; } .fault { color: #F56C6C; animation: blink 1s infinite; }

/* 报告与抽屉样式 */
:deep(.report-dialog .el-dialog) { background: #fff; color: #333; border-radius: 8px; }
:deep(.report-dialog .el-dialog__header) { border-bottom: 1px solid #eee; }
:deep(.el-drawer) { background: #2d2d30 !important; color: #d4d4d4 !important; }
:deep(.el-drawer__header) { color: #ffffff !important; border-bottom: 1px solid #3e3e42; margin-bottom: 0; padding-bottom: 15px;}
:deep(.el-drawer__body) { padding-top: 10px; }
:deep(.el-input__wrapper) { background: #1e1e1e !important; box-shadow: 0 0 0 1px #3e3e42 inset !important; }
:deep(.el-input__inner) { color: #d4d4d4 !important; }
:deep(.el-form-item__label) { color: #bbbbbb !important; }

/* 新增：积木搭建器深色样式 */
.builder-dialog .el-dialog { background: #252526 !important; }
.builder-dialog .el-dialog__header { border-bottom: 1px solid #3e3e42; }
.builder-dialog .el-dialog__title { color: #fff; }
.toolbox-panel { background: #1e1e1e; padding: 10px; border-radius: 4px; border: 1px solid #3e3e42; min-height: 300px; }
.toolbox-title { color: #e5c07b; font-size: 12px; margin-bottom: 10px; font-weight: bold; text-transform: uppercase; }
.toolbox-group { margin-bottom: 15px; }
.canvas-panel { background: #1e1e1e; padding: 15px; border-radius: 4px; border: 1px solid #3e3e42; min-height: 400px; overflow-y: auto; }
.canvas-placeholder { color: #6e7681; text-align: center; margin-top: 150px; font-size: 14px; }
.step-card { background: #2d2d30; border: 1px solid #3e3e42; border-radius: 4px; margin-bottom: 10px; border-left: 4px solid #409EFF; }
.step-card.assertion-card { border-left-color: #F56C6C; }
.step-header { display: flex; align-items: center; padding: 8px 10px; border-bottom: 1px dashed #3e3e42; }
.step-index { color: #6e7681; margin-right: 10px; font-size: 12px; }
.step-actions { margin-left: auto; display: flex; gap: 5px; }
.step-params { padding: 10px; background: #252526; }
</style>