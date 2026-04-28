<!-- frontend/src/views/ReportView.vue -->
<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getNodes, getReportList, getReportDetail } from '@/api'

// ==========================================
// 状态
// ==========================================
const availableNodes = ref([])
const reportListNode = ref('')
const reportList = ref([])
const reportListTotal = ref(0)
const reportListPage = ref(1)
const reportListLoading = ref(false)

const detailVisible = ref(false)
const detailReport = ref(null)
const detailChartRef = ref(null)
const detailChartInst = ref(null)

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

const fetchReportList = async () => {
  reportListLoading.value = true
  try {
    const params = {
      limit: 10,
      offset: (reportListPage.value - 1) * 10,
    }
    if (reportListNode.value) params.node_id = reportListNode.value

    const res = await getReportList(params)
    reportList.value = res.reports || []
    reportListTotal.value = res.total || 0
  } catch (e) {
    ElMessage.error('报告列表获取失败')
  } finally {
    reportListLoading.value = false
  }
}

const viewReportDetail = async (reportId) => {
  try {
    const res = await getReportDetail(reportId)
    detailReport.value = res.report
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
      type: 'pie',
      radius: ['45%', '75%'],
      itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, fontSize: 13, formatter: '{b}\n{d}%' },
      data: [
        {
          value: detailReport.value.pass_count,
          name: '通过',
          itemStyle: { color: '#10B981' },
        },
        {
          value: detailReport.value.fail_count,
          name: '失败',
          itemStyle: { color: '#EF4444' },
        },
        {
          value: detailReport.value.error_count || 0,
          name: '错误',
          itemStyle: { color: '#F59E0B' },
        },
      ],
    }],
  })
}

// ==========================================
// 生命周期
// ==========================================
let nodesTimer = null

onMounted(() => {
  fetchNodes()
  fetchReportList()
  nodesTimer = setInterval(fetchNodes, 5000)
})

onUnmounted(() => {
  if (nodesTimer) clearInterval(nodesTimer)
  if (detailChartInst.value) detailChartInst.value.dispose()
})
</script>

<template>
  <div class="report-view">

    <!-- 筛选工具栏 -->
    <div class="toolbar">
      <span class="toolbar-label">节点筛选：</span>
      <el-select
        v-model="reportListNode"
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

      <div class="toolbar-actions">
        <el-button type="primary" @click="fetchReportList">
          <el-icon><Search /></el-icon>
          查询
        </el-button>
      </div>
    </div>

    <!-- 报告列表 -->
    <div class="table-card">
      <el-table
        :data="reportList"
        v-loading="reportListLoading"
        stripe
        border
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="report_name" label="报告名称" />
        <el-table-column prop="node_id" label="节点" width="140" />
        <el-table-column prop="total_cases" label="总用例" width="80" align="center" />

        <el-table-column prop="pass_count" label="通过" width="80" align="center">
          <template #default="{ row }">
            <span class="count-pass">{{ row.pass_count }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="fail_count" label="失败" width="80" align="center">
          <template #default="{ row }">
            <span class="count-fail">{{ row.fail_count }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="pass_rate" label="通过率" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.pass_rate >= 80 ? 'success' : 'danger'"
              size="small"
            >
              {{ row.pass_rate }}%
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="create_time" label="创建时间" width="170" />

        <el-table-column label="操作" width="100" align="center">
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

    <!-- 报告详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      :title="`报告详情：${detailReport?.report_name}`"
      width="80%"
    >
      <div v-if="detailReport">
        <el-row :gutter="24">
          <el-col :span="8">
            <div ref="detailChartRef" style="height: 240px" />
          </el-col>
          <el-col :span="16">
            <el-descriptions
              :column="3"
              border
              size="small"
              style="margin-bottom: 16px"
            >
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
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<style scoped>
.report-view {
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

/* 数字高亮 */
.count-pass {
  color: var(--color-success);
  font-weight: var(--font-weight-bold);
  font-size: var(--font-md);
}

.count-fail {
  color: var(--color-danger);
  font-weight: var(--font-weight-bold);
  font-size: var(--font-md);
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--spacing-4);
  padding-top: var(--spacing-3);
  border-top: 1px solid var(--border-light);
}
</style>