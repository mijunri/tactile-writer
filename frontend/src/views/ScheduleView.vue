<template>
  <div>
    <div class="page-header">
      <div>
        <h2>定时写作</h2>
        <p class="desc">设置每日自动写作任务，适合微信公众号、头条号等定期更新</p>
      </div>
      <el-button type="primary" @click="showDialog = true">
        <el-icon><Timer /></el-icon> 新建定时任务
      </el-button>
    </div>

    <el-card v-loading="loading">
      <el-empty v-if="!schedules.length" description="还没有定时任务">
        <el-button type="primary" @click="showDialog = true">创建第一个定时任务</el-button>
      </el-empty>
      <el-table v-else :data="schedules">
        <el-table-column prop="name" label="任务名称" min-width="160" />
        <el-table-column prop="cron_expression" label="执行时间" width="140">
          <template #default="{ row }">{{ cronLabel(row.cron_expression) }}</template>
        </el-table-column>
        <el-table-column prop="prompt_template" label="写作要求" min-width="240" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              :model-value="row.enabled"
              @change="(v) => toggleTask(row, v)"
              active-text="开"
              inactive-text="关"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button link type="primary" @click="triggerTask(row)">立即执行</el-button>
            <el-button link type="danger" @click="deleteTask(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showDialog" title="新建定时写作任务" width="560px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="任务名称">
          <el-input v-model="form.name" placeholder="例如：每日科技早报" />
        </el-form-item>
        <el-form-item label="执行时间">
          <el-select v-model="form.cron_preset" style="width: 100%" @change="applyCron">
            <el-option label="每天早上 8:00" value="0 8 * * *" />
            <el-option label="每天中午 12:00" value="0 12 * * *" />
            <el-option label="每天晚上 20:00" value="0 20 * * *" />
            <el-option label="每周一早上 9:00" value="0 9 * * 1" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.cron_preset === 'custom'" label="Cron 表达式">
          <el-input v-model="form.cron_expression" placeholder="0 8 * * *" />
        </el-form-item>
        <el-form-item label="发布平台">
          <el-select v-model="form.platform">
            <el-option label="微信公众号" value="微信公众号" />
            <el-option label="头条号" value="头条号" />
            <el-option label="小红书" value="小红书" />
          </el-select>
        </el-form-item>
        <el-form-item label="写作要求">
          <el-input
            v-model="form.prompt_template"
            type="textarea"
            :rows="4"
            placeholder="例如：根据当天科技热点，写一篇500字左右的科技资讯摘要..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createTask">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Timer } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api/client'

const schedules = ref([])
const loading = ref(false)
const showDialog = ref(false)
const saving = ref(false)
const form = ref({
  name: '',
  cron_preset: '0 8 * * *',
  cron_expression: '0 8 * * *',
  platform: '微信公众号',
  prompt_template: '',
})

const cronLabels = {
  '0 8 * * *': '每天 08:00',
  '0 12 * * *': '每天 12:00',
  '0 20 * * *': '每天 20:00',
  '0 9 * * 1': '每周一 09:00',
}

function cronLabel(expr) {
  return cronLabels[expr] || expr
}

function applyCron(val) {
  if (val !== 'custom') form.value.cron_expression = val
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/schedules')
    schedules.value = data
  } finally {
    loading.value = false
  }
}

async function createTask() {
  if (!form.value.name || !form.value.prompt_template) {
    ElMessage.warning('请填写任务名称和写作要求')
    return
  }
  saving.value = true
  try {
    await api.post('/schedules', {
      name: form.value.name,
      cron_expression: form.value.cron_expression,
      platform: form.value.platform,
      prompt_template: form.value.prompt_template,
    })
    ElMessage.success('定时任务已创建')
    showDialog.value = false
    form.value = { name: '', cron_preset: '0 8 * * *', cron_expression: '0 8 * * *', platform: '微信公众号', prompt_template: '' }
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    saving.value = false
  }
}

async function toggleTask(row, enabled) {
  try {
    await api.post(`/schedules/${row.id}/toggle`, { enabled })
    row.enabled = enabled
    ElMessage.success(enabled ? '已启用' : '已暂停')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function triggerTask(row) {
  try {
    const { data } = await api.post(`/schedules/${row.id}/trigger`)
    ElMessage.success(`已触发，文章 ID: ${data.work_item_id}`)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '触发失败')
  }
}

async function deleteTask(row) {
  await ElMessageBox.confirm(`确定删除「${row.name}」？`, '确认')
  try {
    await api.delete(`/schedules/${row.id}`)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.desc { color: #909399; font-size: 14px; margin-top: 4px; }
</style>
