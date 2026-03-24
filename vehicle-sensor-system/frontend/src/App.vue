<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

// --- 数据状态 ---
const tableData = ref([]) // 表格数据
const realtimeData = ref({ temperature: 0, humidity: 0 }) // 实时数据
let timer = null // 定时器
let chartInstance = null // 图表实例
let lineChartInstance = null // 折线图实例

// --- API 请求 ---
const API_BASE = 'http://127.0.0.1:8000'

// 获取实时数据
const fetchRealtime = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/realtime`)

    // 【关键】打印一下看看拿到了什么
    console.log("API Response:", res.data)

    // 只有数据不为空时才更新
    if (res.data) {
      realtimeData.value = res.data
      updateChart(res.data.temperature)
    } else {
      console.warn("后端返回数据为空")
    }
  } catch (e) {
    console.error('获取实时数据失败', e)
  }
}

// 获取历史数据
const fetchHistory = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/history?limit=20`)
    tableData.value = res.data

    // 【新增】更新折线图
    updateLineChart(res.data)
  } catch (e) {
    console.error('获取历史数据失败', e)
  }
}

// 导出测试报告功能
const exportReport = () => {
  if (tableData.value.length === 0) {
    alert('暂无数据可导出')
    return
  }

  // 1. 定义 CSV 表头
  // 【修改】增加了 "传输延迟" 列
  let csvContent = "\uFEFF采集时间,设备ID,温度(℃),湿度(%),传输延迟,测试结果,异常原因\n"

  // 2. 遍历数据填充
  tableData.value.forEach(row => {
    const time = new Date(row.create_time).toLocaleString()
    const result = row.is_abnormal ? "异常" : "正常"
    const errorMsg = row.error_msg || ""

    // 【新增】获取延迟数值，如果没有则显示 0
    const latency = row.latency || 0

    // 拼接每一行
    // 【修改】增加 latency 字段
    csvContent += `${time},${row.device_id},${row.temperature},${row.humidity},${latency},${result},${errorMsg}\n`
  })

  // 3. 创建 Blob 对象
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })

  // 4. 创建下载链接
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.setAttribute("href", url)
  link.setAttribute("download", `车载传感器测试报告_${new Date().toLocaleDateString()}_${new Date().toLocaleTimeString().replace(/:/g, '-')}.csv`)

  // 5. 触发下载
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  // 6. 清理环境
  document.body.removeChild(link) // 移除链接元素
  URL.revokeObjectURL(url)        // 释放内存
}

// --- 图表逻辑 ---
const initChart = () => {
  const chartDom = document.getElementById('gaugeChart')
  chartInstance = echarts.init(chartDom)

  const option = {
    series: [
      {
        type: 'gauge',
        center: ['50%', '60%'],
        startAngle: 200,
        endAngle: -20,
        min: -40,
        max: 100,
        splitNumber: 14,
        itemStyle: {
          color: '#FF4500' // 指针颜色
        },
        progress: {
          show: true,
          width: 20
        },
        pointer: {
          show: true
        },
        axisLine: {
          lineStyle: {
            width: 20
          }
        },
        axisTick: {
          distance: -30,
          splitNumber: 5,
          lineStyle: {
            width: 2,
            color: '#999'
          }
        },
        splitLine: {
          distance: -35,
          length: 14,
          lineStyle: {
            width: 3,
            color: '#999'
          }
        },
        axisLabel: {
          distance: -20,
          color: '#999',
          fontSize: 12
        },
        anchor: {
          show: true,
          showAbove: true,
          size: 20,
          itemStyle: {
            borderWidth: 8,
            borderColor: '#AC1CB2'
          }
        },
        title: {
          show: false
        },
        detail: {
          valueAnimation: true,
          width: '60%',
          lineHeight: 40,
          borderRadius: 8,
          offsetCenter: [0, '-15%'],
          fontSize: 30,
          fontWeight: 'bolder',
          formatter: '{value} °C',
          color: 'inherit'
        },
        data: [
          {
            value: 25
          }
        ]
      }
    ]
  }

  chartInstance.setOption(option)
}

const updateChart = (value) => {
  if (chartInstance) {
    chartInstance.setOption({
      series: [
        {
          data: [
            {
              value: value.toFixed(1)
            }
          ]
        }
      ]
    })
  }
}
// 【新增】2. 折线图初始化
const initLineChart = () => {
  const chartDom = document.getElementById('lineChart')
  lineChartInstance = echarts.init(chartDom)

  const option = {
    title: { text: '温度变化趋势', left: 'center' },
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: [] // 初始为空
    },
    yAxis: {
      type: 'value',
      name: '温度(℃)'
    },
    series: [
      {
        name: '温度',
        type: 'line',
        smooth: true,
        itemStyle: { color: '#409EFF' },
        data: [] // 初始为空
      }
    ]
  }
  lineChartInstance.setOption(option)
}

// 【新增】3. 折线图数据更新
const updateLineChart = (data) => {
  if (!lineChartInstance) return

  // 数据是按时间倒序来的（最新在前），图表需要从左到右（最旧在前），所以要反转
  const sortedData = [...data].reverse()

  const times = sortedData.map(item => {
    // 只显示时分秒，让横轴清爽一点
    return new Date(item.create_time).toLocaleTimeString()
  })

  const temps = sortedData.map(item => item.temperature)

  lineChartInstance.setOption({
    xAxis: { data: times },
    series: [{ data: temps }]
  })
}

// 测试任务状态
const testStatus = ref({
  is_active: false,
  total_count: 0
})

// 开始测试
const startTest = async () => {
  await axios.post(`${API_BASE}/api/test/start`)
  refreshStatus()
}

// 报告相关数据
const reportDialogVisible = ref(false)
const currentReport = ref({})

// 结束测试
const stopTest = async () => {
  try {
    const res = await axios.post(`${API_BASE}/api/test/stop`)
    if (res.data) {
      currentReport.value = res.data // 保存报告数据
      reportDialogVisible.value = true // 打开弹窗
      refreshStatus()
      fetchHistory()
    }
  } catch (e) {
    alert('结束测试失败')
  }
}

// 打印报告功能
const printReport = () => {
  window.print()
}

// 获取状态
const refreshStatus = async () => {
  const res = await axios.get(`${API_BASE}/api/test/status`)
  testStatus.value = res.data
}

// 配置表单数据
const configForm = ref({
  temp_min: -40,
  temp_max: 85,
  hum_min: 0,
  hum_max: 100,
  temp_change_limit: 5,
  hum_change_limit: 10,
  lost_timeout: 5
})

// 获取配置
const fetchConfig = async () => {
  const res = await axios.get(`${API_BASE}/api/config`)
  if (res.data) {
    configForm.value = res.data
  }
}

// 保存配置
const saveConfig = async () => {
  try {
    await axios.post(`${API_BASE}/api/config`, configForm.value)
    alert('规则配置已生效！')
  } catch (e) {
    alert('配置保存失败')
  }
}

// 在 onMounted 中加入状态轮询
onMounted(() => {
  initChart()        // 初始化仪表盘
  initLineChart()    // 初始化折线图
  fetchHistory()     // 拉取历史数据
  fetchRealtime()    // 拉取实时数据
  fetchConfig() // 加载配置
  // 定时轮询
  timer = setInterval(() => {
    fetchRealtime()
    fetchHistory()
  }, 2000)

  refreshStatus()
  setInterval(refreshStatus, 1000) // 每秒刷新一次状态
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (chartInstance) chartInstance.dispose()
  if (lineChartInstance) lineChartInstance.dispose() // 销毁实例
})
</script>

<template>
  <div style="padding: 20px; background: #f5f5f5; min-height: 100vh;">
    <!-- 修改这一块：使用 flex 布局让标题和按钮分居两侧 -->
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
      <h1 style="margin: 0; color: #333;">车载传感器远程测试系统</h1>

      <!-- 【新增】导出按钮 -->
      <!-- 添加 native-type="button" 和 @click.prevent -->
      <el-button type="primary" native-type="button" @click.prevent="exportReport">
        导出测试报告
      </el-button>
    </div>
    <!-- 左侧：测试控制台 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="24">
        <el-card shadow="hover" style="background: #fff;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <span style="font-weight: bold; margin-right: 20px;">测试状态：</span>
              <el-tag :type="testStatus.is_active ? 'success' : 'info'" size="large">
                {{ testStatus.is_active ? '测试进行中...' : '待机中' }}
              </el-tag>
              <span style="margin-left: 20px; color: #666;">
                已采集数据: {{ testStatus.total_count }} 条
              </span>
            </div>
            <div>
              <el-button
                type="success"
                size="large"
                @click="startTest"
                :disabled="testStatus.is_active"
                icon="VideoPlay">
                开始测试
              </el-button>
              <el-button
                type="danger"
                size="large"
                @click="stopTest"
                :disabled="!testStatus.is_active"
                icon="VideoPause">
                结束测试
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <!-- 右侧：规则配置 -->
    <el-col :span="12">
      <el-card shadow="hover">
        <template #header>
          <span>测试规则配置</span>
        </template>

        <el-form :model="configForm" label-width="120px" size="small">
          <el-row>
            <el-col :span="12">
              <el-form-item label="温度下限 (℃)">
                <el-input v-model="configForm.temp_min" type="number"></el-input>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="温度上限 (℃)">
                <el-input v-model="configForm.temp_max" type="number"></el-input>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row>
            <el-col :span="12">
              <el-form-item label="突变阈值 (℃)">
                <el-input v-model="configForm.temp_change_limit" type="number"></el-input>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="丢包超时 (秒)">
                <el-input v-model="configForm.lost_timeout" type="number"></el-input>
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item>
            <el-button type="primary" @click="saveConfig">应用配置</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </el-col>
    <!-- 【新增】测试报告弹窗 -->
    <el-dialog
      v-model="reportDialogVisible"
      title="车载传感器测试报告"
      width="50%"
      center>

      <div class="report-container" id="printArea">
        <el-descriptions title="测试概览" :column="2" border>
          <el-descriptions-item label="测试开始时间">
            {{ new Date(currentReport.start_time).toLocaleString() }}
          </el-descriptions-item>
          <el-descriptions-item label="测试结束时间">
            {{ new Date(currentReport.end_time).toLocaleString() }}
          </el-descriptions-item>
          <el-descriptions-item label="测试时长">
            {{ currentReport.duration }}
          </el-descriptions-item>
          <el-descriptions-item label="测试数据总量">
            {{ currentReport.total_count }} 条
          </el-descriptions-item>
        </el-descriptions>

        <el-divider />

        <el-descriptions title="测试结果" :column="3" border>
          <el-descriptions-item label="异常数据量">
            <el-tag type="danger" size="large">{{ currentReport.abnormal_count }} 条</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="数据通过率">
            <el-tag :type="currentReport.pass_rate >= 95 ? 'success' : 'warning'" size="large">
              {{ currentReport.pass_rate }} %
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="平均传输延迟">
            <el-tag type="info" size="large">{{ currentReport.avg_latency }} ms</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <el-divider />

        <div style="text-align: center; margin-top: 20px;">
          <h3>综合测试结论：</h3>
          <el-tag
            :type="currentReport.conclusion === '通过' ? 'success' : 'danger'"
            size="large"
            style="font-size: 20px; padding: 10px 20px;">
            {{ currentReport.conclusion }}
          </el-tag>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="reportDialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="printReport">打印报告</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 核心展示区 -->
    <el-row :gutter="20" style="margin-top: 20px;">

      <!-- 左侧：实时仪表盘 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>实时温度监控</span>
              <el-tag :type="realtimeData.is_abnormal ? 'danger' : 'success'">
                {{ realtimeData.is_abnormal ? '异常报警' : '正常' }}
              </el-tag>
            </div>
          </template>
          <div id="gaugeChart" style="width: 100%; height: 400px;"></div>
          <div style="text-align: center; margin-top: 20px; font-size: 16px;">
            当前湿度: <b>{{ realtimeData.humidity }} %</b> <br>
            <!-- 【新增】显示延迟 -->
            <span :style="{ color: realtimeData.latency > 500 ? 'red' : 'green' }">
              传输延迟: <b>{{ realtimeData.latency || 0 }} ms</b>
            </span>
            <br>
            更新时间: {{ new Date(realtimeData.create_time).toLocaleString() }}
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：历史数据表格 -->
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <span>测试记录列表</span>
          </template>
          <el-table :data="tableData" height="450" stripe style="width: 100%">
            <el-table-column prop="temperature" label="温度 (℃)" width="100" />
            <el-table-column prop="humidity" label="湿度 (%)" width="100" />
            <el-table-column label="测试结果">
              <template #default="scope">
                <el-tag v-if="scope.row.is_abnormal" type="danger">异常</el-tag>
                <el-tag v-else type="success">正常</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="error_msg" label="异常原因" show-overflow-tooltip />
            <el-table-column label="时间" width="150">
               <template #default="scope">
                 {{ new Date(scope.row.create_time).toLocaleTimeString() }}
               </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

     <!-- 趋势图 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <el-card shadow="hover">
          <div id="lineChart" style="width: 100%; height: 350px;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
@media print {
  /* 打印时隐藏弹窗的按钮和页面背景 */
  body * {
    visibility: hidden;
  }
  #printArea, #printArea * {
    visibility: visible;
  }
  #printArea {
    position: absolute;
    left: 0;
    top: 0;
  }
}
</style>