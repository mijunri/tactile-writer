<template>
  <div>
    <div class="page-header">
      <h2>我的文章</h2>
      <el-button type="primary" @click="$router.push('/write')">
        <el-icon><EditPen /></el-icon> 新建文章
      </el-button>
    </div>

    <el-row :gutter="16" class="stats">
      <el-col :span="8">
        <el-card shadow="hover"><div class="stat-num">{{ articles.length }}</div><div class="stat-label">全部文章</div></el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover"><div class="stat-num">{{ runningCount }}</div><div class="stat-label">生成中</div></el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover"><div class="stat-num">{{ doneCount }}</div><div class="stat-label">已完成</div></el-card>
      </el-col>
    </el-row>

    <el-card v-loading="loading" style="margin-top: 16px">
      <el-empty v-if="!articles.length" description="还没有文章，点击上方按钮开始写作" />
      <el-table v-else :data="articles" @row-click="openArticle" style="cursor:pointer">
        <el-table-column prop="name" label="标题" min-width="200" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row)" size="small">{{ statusLabel(row) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="openArticle(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { EditPen } from '@element-plus/icons-vue'
import api from '../api/client'

const router = useRouter()
const articles = ref([])
const loading = ref(false)

const runningCount = computed(() => articles.value.filter(a => ['pending','scheduled','running'].includes(a.status)).length)
const doneCount = computed(() => articles.value.filter(a => ['idle','completed'].includes(a.status)).length)

function statusType(row) {
  if (row.status === 'running') return 'warning'
  if (row.status === 'failed') return 'danger'
  if (row.status === 'idle') return 'success'
  return 'info'
}

function statusLabel(row) {
  const map = { pending: '等待中', scheduled: '调度中', running: '写作中', idle: '已完成', failed: '失败' }
  return map[row.status] || row.status
}

function formatTime(t) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

function openArticle(row) {
  router.push(`/write/${row.id}`)
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/articles')
    articles.value = data.sort((a, b) => new Date(b.create_time) - new Date(a.create_time))
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.stats .stat-num { font-size: 28px; font-weight: 700; color: #409eff; }
.stats .stat-label { color: #909399; font-size: 13px; margin-top: 4px; }
</style>
