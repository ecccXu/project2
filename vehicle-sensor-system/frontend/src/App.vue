<!-- src/App.vue -->
<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

const API_BASE = 'http://127.0.0.1:8000'

// --- 数据状态 ---
const tableData = ref([])
const realtimeData = ref(null) // 初始为空，等待后端返回
let timer = null
let chartInstance = null
let lineChartInstance = null

// --- API 请求 ---
const fetchRealtime = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/realtime`)
    if (res.data) {
      realtimeData.value = res.data
      updateChart(res.data.in_car_temp)
    }
  } catch (e) { console.error('获取实时数据失败', e) }
}

const fetchHistory = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/history?limit=30`)
    tableData.value = res.data
    updateLineChart(res.data)
  } catch (e) { console.error('获取历史数据失败', e) }
}

// --- 导出报告 ---
const exportReport = () => {
  if (!tableData.value.length) return alert('暂无数据可导出')
  let csvContent = "\uFEFF采集时间,设备ID,车内温(℃),车外温(℃),湿度(%),PM2.5,CO2(ppm),硬件状态,测试结果,异常原因\n"
  tableData.value.forEach(row => {
    const time = new Date(row.create_time).toLocaleString()
    const result = row.is_abnormal ? "异常" : "正常"
    csvContent += `${time},${row.sensor_id},${row.in_car_temp},${row.out_car_temp},${row.humidity},${row.pm25},${row.co2},${row.status},${result},"${row.error_msg || ''}"\n`
  })
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.setAttribute("href", url)
  link.setAttribute("download", `车载传感器测试报告_${new Date().toLocaleDateString()}.csv`)
  link.click()
  URL.revokeObjectURL(url)
}

// --- 仪表盘逻辑 ---
const initChart = () => {
  chartInstance = echarts.init(document.getElementById('gaugeChart'))
  chartInstance.setOption({
    series: [{
      type: 'gauge', center: ['50%', '60%'], startAngle: 200, endAngle: -20,
      min: -40, max: 85, splitNumber: 12,
      itemStyle: { color: '#409EFF' }, progress: { show: true, width: 18 },
      pointer: { show: true }, axisLine: { lineStyle: { width: 18 } },
      axisTick: { distance: -25, splitNumber: 5, lineStyle: { width: 1, color: '#999' } },
      splitLine: { distance: -30, length: 10, lineStyle: { width: 2, color: '#999' } },
      axisLabel: { distance: -15, color: '#999', fontSize: 10 },
      detail: { valueAnimation: true, width: '60%', lineHeight: 30, borderRadius: 8, offsetCenter: [0, '-10%'], fontSize: 24, fontWeight: 'bolder', formatter: '{value} °C', color: 'inherit' },
      data: [{ value: 25 }]
    }]
  })
}
const updateChart = (value) => {
  if (chartInstance) chartInstance.setOption({ series: [{ data: [{ value: value ? value.toFixed(1) : 0 }] }] })
}

// --- 折线图逻辑 (双Y轴：温度 vs 空气质量) ---
const initLineChart = () => {
  lineChartInstance = echarts.init(document.getElementById('lineChart'))
  lineChartInstance.setOption({
    title: { text: '多维数据变化趋势', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['车内温度', 'PM2.5', 'CO2'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: [] },
    yAxis: [
      { type: 'value', name: '温度(℃)', position: 'left' },
      { type: 'value', name: '空气质量', position: 'right', max: 2500 }
    ],
    series: [
      { name: '车内温度', type: 'line', smooth: true, yAxisIndex: 0, itemStyle: { color: '#409EFF' }, data: [] },
      { name: 'PM2.5', type: 'line', smooth: true, yAxisIndex: 1, itemStyle: { color: '#E6A23C' }, data: [] },
      { name: 'CO2', type: 'line', smooth: true, yAxisIndex: 1, itemStyle: { color: '#F56C6C' }, lineStyle: { type: 'dashed' }, data: [] }
    ]
  })
}
const updateLineChart = (data) => {
  if (!lineChartInstance || !data.length) return
  const sortedData = [...data].reverse()
  const times = sortedData.map(item => new Date(item.create_time).toLocaleTimeString())
  lineChartInstance.setOption({
    xAxis: { data: times },
    series: [
      { data: sortedData.map(item => item.in_car_temp) },
      { data: sortedData.map(item => item.pm25) },
      { data: sortedData.map(item => item.co2) }
    ]
  })
}

// --- 测试任务控制 ---
const testStatus = ref({ is_active: false, total_count: 0 })
const reportDialogVisible = ref(false)
const currentReport = ref({})

const startTest = async () => { await axios.post(`${API_BASE}/api/test/start`); refreshStatus() }
const stopTest = async () => {
  const res = await axios.post(`${API_BASE}/api/test/stop`)
  if (res.data && res.data.conclusion) {
    currentReport.value = res.data; reportDialogVisible.value = true; refreshStatus(); fetchHistory()
  }
}
const refreshStatus = async () => { testStatus.value = (await axios.get(`${API_BASE}/api/test/status`)).data }
const printReport = () => window.print()

// --- 规则配置 ---
const configForm = ref({
  temp_min: -40, temp_max: 85, hum_min: 0, hum_max: 100,
  temp_change_limit: 5, pm25_change_limit: 30, pm25_max: 75, co2_max: 1000, lost_timeout: 5
})
const fetchConfig = async () => { const res = await axios.get(`${API_BASE}/api/config`); if(res.data) configForm.value = res.data }
const saveConfig = async () => {
  try { await axios.post(`${API_BASE}/api/config`, configForm.value); alert('规则配置已生效！') }
  catch (e) { alert('配置保存失败') }
}

// --- 模拟器工况与故障控制 ---
const sendCommand = async (command, params) => {
  try {
    await axios.post(`${API_BASE}/api/simulator/control`, { command, params })
  } catch (e) { alert('指令下发失败，请检查后端') }
}
const clearFault = () => sendCommand('clear_fault', {})
const setScenario = (name) => sendCommand('set_scenario', { scenario: name })
const injectStuck = () => sendCommand('inject_fault', { target: 'pm25', fault_type: 'STUCK', stuck_value: 75.0 })
const injectOpen = () => sendCommand('inject_fault', { target: 'in_car_temp', fault_type: 'OPEN_CIRCUIT' })

// --- 生命周期 ---
onMounted(() => {
  initChart(); initLineChart(); fetchHistory(); fetchRealtime(); fetchConfig(); refreshStatus()
  timer = setInterval(() => { fetchRealtime(); fetchHistory() }, 2000)
  setInterval(refreshStatus, 1000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (chartInstance) chartInstance.dispose()
  if (lineChartInstance) lineChartInstance.dispose()
})
</script>

<template>
  <div style="padding: 20px; background: #f0f2f5; min-height: 100vh; font-family: sans-serif;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
      <h1 style="margin: 0; color: #333;">车载环境传感器自动化测试系统</h1>
      <el-button type="primary" @click="exportReport">导出测试报告(CSV)</el-button>
    </div>

    <!-- 测试状态控制台 -->
    <el-card shadow="hover" style="margin-bottom: 20px; background: #fff;">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <span style="font-weight: bold; margin-right: 15px;">测试状态：</span>
          <el-tag :type="testStatus.is_active ? 'success' : 'info'" size="large">
            {{ testStatus.is_active ? '数据采集中...' : '待机中' }}
          </el-tag>
          <span style="margin-left: 20px; color: #666;">已采集: {{ testStatus.total_count }} 条</span>
        </div>
        <div>
          <el-button type="success" size="large" @click="startTest" :disabled="testStatus.is_active" icon="VideoPlay">开始测试</el-button>
          <el-button type="danger" size="large" @click="stopTest" :disabled="!testStatus.is_active" icon="VideoPause">结束并生成报告</el-button>
        </div>
      </div>
    </el-card>

    <el-row :gutter="20" style="margin-bottom: 20px;">
      <!-- 工况控制面板 (新增) -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>模拟器工况控制</span></template>
          <el-space wrap>
            <el-button @click="setScenario('static_parking_summer')">夏日静置</el-button>
            <el-button @click="setScenario('winter_cruising')">冬季巡航</el-button>
            <el-button @click="setScenario('tunnel_following')">隧道跟车</el-button>
            <el-button @click="setScenario('highway_ac_leak')">空调漏气</el-button>
            <el-divider direction="vertical" />
            <el-button type="warning" @click="injectStuck">注入PM2.5卡滞</el-button>
            <el-button type="danger" @click="injectOpen">注入温度断路</el-button>
            <el-button type="info" @click="clearFault">清除所有故障</el-button>
          </el-space>
        </el-card>
      </el-col>

      <!-- 规则配置面板 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>测试规则阈值配置</span></template>
          <el-form :model="configForm" label-width="100px" size="small">
            <el-row :gutter="10">
              <el-col :span="8"><el-form-item label="温度下限"><el-input v-model="configForm.temp_min" type="number"></el-input></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="温度上限"><el-input v-model="configForm.temp_max" type="number"></el-input></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="温变阈值"><el-input v-model="configForm.temp_change_limit" type="number"></el-input></el-form-item></el-col>
            </el-row>
            <el-row :gutter="10">
              <el-col :span="8"><el-form-item label="PM2.5上限"><el-input v-model="configForm.pm25_max" type="number"></el-input></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="CO2上限"><el-input v-model="configForm.co2_max" type="number"></el-input></el-form-item></el-col>
              <el-col :span="8"><el-form-item label-width="0"><el-button type="primary" @click="saveConfig" style="width:100%">应用配置</el-button></el-form-item></el-col>
            </el-row>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <!-- 核心数据展示区 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <!-- 左侧：实时仪表盘 + 关键数值 -->
      <el-col :span="8">
        <el-card shadow="hover" style="text-align: center;">
          <template #header>
            <div style="display:flex; justify-content:space-between;">
              <span>车内温度仪表</span>
              <el-tag :type="realtimeData && realtimeData.is_abnormal ? 'danger' : 'success'" size="small">
                {{ realtimeData && realtimeData.is_abnormal ? '系统报警' : '状态正常' }}
              </el-tag>
            </div>
          </template>
          <div id="gaugeChart" style="width: 100%; height: 280px;"></div>
          <div style="margin-top: 10px; color: #666; font-size: 13px;">
            硬件状态: <b>{{ realtimeData ? realtimeData.status : '--' }}</b> |
            故障码: <b style="color: red">{{ realtimeData && realtimeData.fault_code !== 'NONE' ? realtimeData.fault_code : '无' }}</b>
          </div>
        </el-card>
      </el-col>

      <!-- 中间：多指标数据卡片 -->
      <el-col :span="8">
        <el-row :gutter="10">
          <el-col :span="12" style="margin-bottom: 10px;">
            <el-card shadow="hover" style="background: #e6f7ff; border-color: #91d5ff;">
              <div style="font-size: 13px; color: #666;">车外温度</div>
              <div style="font-size: 24px; font-weight: bold; color: #1890ff;">{{ realtimeData ? realtimeData.out_car_temp.toFixed(1) : '--' }} ℃</div>
            </el-card>
          </el-col>
          <el-col :span="12" style="margin-bottom: 10px;">
            <el-card shadow="hover" style="background: #f6ffed; border-color: #b7eb8f;">
              <div style="font-size: 13px; color: #666;">车内湿度</div>
              <div style="font-size: 24px; font-weight: bold; color: #52c41a;">{{ realtimeData ? realtimeData.humidity.toFixed(1) : '--' }} %</div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="hover" style="background: #fffbe6; border-color: #ffe58f;">
              <div style="font-size: 13px; color: #666;">PM2.5 浓度</div>
              <div style="font-size: 24px; font-weight: bold; color: #faad14;">{{ realtimeData ? realtimeData.pm25.toFixed(1) : '--' }} ug/m³</div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="hover" style="background: #fff1f0; border-color: #ffa39e;">
              <div style="font-size: 13px; color: #666;">CO2 浓度</div>
              <div style="font-size: 24px; font-weight: bold; color: #f5222d;">{{ realtimeData ? realtimeData.co2.toFixed(1) : '--' }} ppm</div>
            </el-card>
          </el-col>
        </el-row>
        <el-card shadow="hover" style="margin-top: 10px; text-align: center;">
          <span style="color: #888; font-size: 12px;">网络延迟: </span>
          <span :style="{ color: (realtimeData && realtimeData.latency > 500) ? 'red' : 'green', fontWeight: 'bold' }">
            {{ realtimeData ? realtimeData.latency : 0 }} ms
          </span>
        </el-card>
      </el-col>

      <!-- 右侧：历史表格 -->
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>异常捕获记录</span></template>
          <el-table :data="tableData.filter(r => r.is_abnormal).slice(0, 5)" height="320" size="small" stripe>
            <el-table-column prop="in_car_temp" label="温度" width="60" />
            <el-table-column prop="pm25" label="PM2.5" width="60" />
            <el-table-column prop="status" label="硬件" width="60">
              <template #default="scope">
                <el-tag :type="scope.row.status === 'FAULT' ? 'danger' : 'info'" size="small">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="error_msg" label="异常原因" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势图 -->
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card shadow="hover">
          <div id="lineChart" style="width: 100%; height: 350px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 报告弹窗 -->
    <el-dialog v-model="reportDialogVisible" title="自动化测试结题报告" width="50%" center>
      <div id="printArea">
        <el-descriptions title="测试概览" :column="2" border>
          <el-descriptions-item label="开始时间">{{ new Date(currentReport.start_time).toLocaleString() }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ new Date(currentReport.end_time).toLocaleString() }}</el-descriptions-item>
          <el-descriptions-item label="持续时长">{{ currentReport.duration }}</el-descriptions-item>
          <el-descriptions-item label="数据总量">{{ currentReport.total_count }} 条</el-descriptions-item>
        </el-descriptions>
        <el-divider />
        <el-descriptions title="核心指标" :column="3" border>
          <el-descriptions-item label="异常数据量"><el-tag type="danger">{{ currentReport.abnormal_count }} 条</el-tag></el-descriptions-item>
          <el-descriptions-item label="数据通过率"><el-tag :type="currentReport.pass_rate >= 95 ? 'success' : 'warning'">{{ currentReport.pass_rate }} %</el-tag></el-descriptions-item>
          <el-descriptions-item label="平均延迟"><el-tag type="info">{{ currentReport.avg_latency }} ms</el-tag></el-descriptions-item>
        </el-descriptions>
        <div style="text-align: center; margin-top: 20px;">
          <h3>综合结论：</h3>
          <el-tag :type="currentReport.conclusion === '通过' ? 'success' : 'danger'" size="large" style="font-size: 20px; padding: 10px 20px;">
            {{ currentReport.conclusion }}
          </el-tag>
        </div>
      </div>
      <template #footer>
        <el-button @click="reportDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="printReport">打印本页</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
@media print {
  body * { visibility: hidden; }
  #printArea, #printArea * { visibility: visible; }
  #printArea { position: absolute; left: 0; top: 0; width: 100%; }
}
</style>