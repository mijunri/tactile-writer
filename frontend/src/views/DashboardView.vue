<template>
  <div>
    <div class="page-header">
      <h2>我的文章</h2>
      <el-button type="primary" @click="$router.push('/write')">
        <el-icon><EditPen /></el-icon> 新建文章
      </el-button>
    </div>

    <el-tabs v-model="tab">
      <el-tab-pane label="已存档" name="saved">
        <el-card v-loading="loadingSaved">
          <el-empty v-if="!saved.length" description="暂无存档文章（Agent 写完后会通过 Skill 自动上传）" />
          <el-table v-else :data="saved" @row-click="openSaved" style="cursor:pointer">
            <el-table-column prop="title" label="标题" min-width="200" />
            <el-table-column prop="platform" label="平台" width="120" />
            <el-table-column prop="create_time" label="存档时间" width="180">
              <template #default="{ row }">{{ formatTime(row.create_time) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
      <el-tab-pane label="写作中" name="progress">
        <el-card v-loading="loadingProgress">
          <el-empty v-if="!inProgress.length" description="没有进行中的任务" />
          <el-table v-else :data="inProgress" @row-click="openWork" style="cursor:pointer">
            <el-table-column prop="name" label="任务" min-width="160" />
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-tag size="small">{{ statusLabel(row) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="create_time" label="创建时间" width="180">
              <template #default="{ row }">{{ formatTime(row.create_time) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { EditPen } from '@element-plus/icons-vue'
import api from '../api/client'

const router = useRouter()
const tab = ref('saved')
const saved = ref([])
const inProgress = ref([])
const loadingSaved = ref(false)
const loadingProgress = ref(false)

function formatTime(t) {
  return t ? new Date(t).toLocaleString('zh-CN') : '-'
}

function statusLabel(row) {
  const m = { pending: '等待', running: '写作中', idle: '已完成', failed: '失败' }
  return m[row.status] || row.status
}

function openSaved(row) {
  router.push(`/article/${row.id}`)
}

function openWork(row) {
  router.push(`/write/${row.id}`)
}

async function load() {
  loadingSaved.value = true
  loadingProgress.value = true
  try {
    const [s, p] = await Promise.all([
      api.get('/articles/saved'),
      api.get('/articles/in-progress'),
    ])
    saved.value = s.data
    inProgress.value = p.data
  } finally {
    loadingSaved.value = false
    loadingProgress.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
