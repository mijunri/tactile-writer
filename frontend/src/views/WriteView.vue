<template>
  <div class="write-page">
    <div v-if="!articleId" class="new-article">
      <h2>对话写作</h2>
      <p class="desc">告诉 AI 你想写什么，支持微信公众号、头条号等平台风格</p>
      <el-card>
        <el-form :model="form" label-width="80px" @submit.prevent="createArticle">
          <el-form-item label="平台">
            <el-select v-model="form.platform" style="width: 200px">
              <el-option label="微信公众号" value="微信公众号" />
              <el-option label="头条号" value="头条号" />
              <el-option label="小红书" value="小红书" />
              <el-option label="知乎" value="知乎" />
              <el-option label="通用" value="通用自媒体" />
            </el-select>
          </el-form-item>
          <el-form-item label="标题">
            <el-input v-model="form.name" placeholder="文章标题（可选）" />
          </el-form-item>
          <el-form-item label="写作要求">
            <el-input
              v-model="form.topic"
              type="textarea"
              :rows="5"
              placeholder="例如：写一篇关于春季养生的文章，目标读者是30-50岁女性，语气亲切..."
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" size="large" :loading="creating" native-type="submit">
              开始写作
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <div v-else class="chat-area">
      <div class="chat-header">
        <el-button text @click="$router.push('/write')">← 新建</el-button>
        <span class="article-name">{{ article?.name || '文章' }}</span>
        <el-tag v-if="article" :type="statusType" size="small">{{ statusText }}</el-tag>
      </div>

      <div ref="messagesEl" class="messages" v-loading="loadingHistory">
        <div v-for="(msg, i) in messages" :key="i" :class="['msg', msg.role]">
          <div class="msg-role">{{ msg.role === 'user' ? '我' : '写作助手' }}</div>
          <div class="msg-content" v-html="renderMd(msg.content)"></div>
        </div>
        <div v-if="!messages.length && !loadingHistory" class="empty-hint">
          <el-empty description="AI 正在准备写作环境，请稍候..." />
        </div>
      </div>

      <div class="input-area">
        <el-input
          v-model="input"
          type="textarea"
          :rows="3"
          placeholder="继续对话，例如：把第二段改得更口语化一些..."
          :disabled="sending"
          @keydown.ctrl.enter="sendMessage"
        />
        <el-button type="primary" :loading="sending" :disabled="!input.trim()" @click="sendMessage">
          发送 (Ctrl+Enter)
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import api from '../api/client'

const route = useRoute()
const router = useRouter()

const articleId = computed(() => route.params.id ? Number(route.params.id) : null)
const form = ref({ platform: '微信公众号', name: '新文章', topic: '' })
const creating = ref(false)
const article = ref(null)
const messages = ref([])
const input = ref('')
const sending = ref(false)
const loadingHistory = ref(false)
const messagesEl = ref(null)
let pollTimer = null

const statusText = computed(() => {
  if (!article.value) return ''
  const map = { pending: '准备中', running: '写作中', idle: '已完成', failed: '失败' }
  return map[article.value.status] || article.value.status
})

const statusType = computed(() => {
  if (!article.value) return 'info'
  if (article.value.status === 'running') return 'warning'
  if (article.value.status === 'idle') return 'success'
  if (article.value.status === 'failed') return 'danger'
  return 'info'
})

function renderMd(text) {
  if (!text) return ''
  return marked.parse(text, { breaks: true })
}

async function createArticle() {
  if (!form.value.topic.trim()) {
    ElMessage.warning('请填写写作要求')
    return
  }
  creating.value = true
  try {
    const { data } = await api.post('/articles', form.value)
    router.push(`/write/${data.id}`)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

async function loadArticle() {
  if (!articleId.value) return
  const { data } = await api.get(`/articles/${articleId.value}`)
  article.value = data
}

async function loadHistory() {
  if (!articleId.value) return
  loadingHistory.value = true
  try {
    const { data } = await api.get(`/articles/${articleId.value}/chat/history`)
    messages.value = data
    await nextTick()
    scrollBottom()
  } finally {
    loadingHistory.value = false
  }
}

async function pollStatus() {
  if (!articleId.value) return
  try {
    const { data } = await api.get(`/articles/${articleId.value}/chat/status`)
    if (article.value) {
      article.value.status = data.work_status || article.value.status
      article.value.sandbox_status = data.sandbox_status
    }
    await loadHistory()
  } catch { /* ignore */ }
}

function scrollBottom() {
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

async function sendMessage() {
  if (!input.value.trim() || sending.value) return
  const content = input.value.trim()
  input.value = ''
  messages.value.push({ role: 'user', content })
  await nextTick()
  scrollBottom()
  sending.value = true
  try {
    await api.post(`/articles/${articleId.value}/chat/send`, { content })
    await loadHistory()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '发送失败')
  } finally {
    sending.value = false
  }
}

watch(articleId, async (id) => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (id) {
    await loadArticle()
    await loadHistory()
    pollTimer = setInterval(pollStatus, 5000)
  }
}, { immediate: true })

onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<style scoped>
.write-page { height: calc(100vh - 108px); display: flex; flex-direction: column; }
.new-article { max-width: 700px; margin: 0 auto; }
.new-article h2 { margin-bottom: 8px; }
.desc { color: #909399; margin-bottom: 24px; }
.chat-area { display: flex; flex-direction: column; height: 100%; background: #fff; border-radius: 12px; overflow: hidden; border: 1px solid #ebeef5; }
.chat-header { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-bottom: 1px solid #ebeef5; }
.article-name { font-weight: 600; flex: 1; }
.messages { flex: 1; overflow-y: auto; padding: 16px; }
.msg { margin-bottom: 16px; }
.msg.user .msg-content { background: #ecf5ff; }
.msg.assistant .msg-content { background: #f4f4f5; }
.msg-role { font-size: 12px; color: #909399; margin-bottom: 4px; }
.msg-content { padding: 12px 16px; border-radius: 8px; line-height: 1.7; font-size: 14px; }
.msg-content :deep(h1), .msg-content :deep(h2), .msg-content :deep(h3) { margin: 12px 0 8px; }
.msg-content :deep(p) { margin: 8px 0; }
.input-area { padding: 12px 16px; border-top: 1px solid #ebeef5; display: flex; gap: 12px; align-items: flex-end; }
.input-area .el-textarea { flex: 1; }
</style>
