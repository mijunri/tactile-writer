<template>
  <div class="write-page">
    <!-- 新建文章 -->
    <div v-if="!articleId" class="new-article">
      <h2>对话写作</h2>
      <p class="desc">左侧与 AI 对话，右侧实时预览成稿</p>
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

    <!-- 左右分栏：对话 + 文章预览 -->
    <div v-else class="split-layout">
      <header class="write-header">
        <el-button text @click="$router.push('/write')">← 新建</el-button>
        <div class="title-block">
          <h1>{{ draft.title || article?.name || '对话写作' }}</h1>
          <el-tag :type="statusTagType" size="small">{{ statusLabel }}</el-tag>
        </div>
      </header>

      <div class="split-pane">
        <!-- 左侧对话 -->
        <section class="chat-panel">
          <div class="panel-head">
            <span class="panel-title">对话</span>
            <span class="panel-hint">描述主题、风格，AI 在右侧生成文章</span>
          </div>

          <div ref="messagesEl" class="chat-messages" v-loading="loadingHistory">
            <div v-if="!messages.length && !loadingHistory" class="empty-chat">
              <p>AI 正在准备写作环境…</p>
              <p class="hint">环境就绪后即可继续对话</p>
            </div>

            <div
              v-for="(msg, i) in messages"
              :key="i"
              class="msg-row"
              :class="msg.role"
            >
              <div class="avatar">{{ msg.role === 'user' ? '你' : '墨' }}</div>
              <div class="bubble">
                <div class="bubble-text">{{ msg.content }}</div>
              </div>
            </div>

            <div v-if="chatStatus === 'running'" class="msg-row assistant">
              <div class="avatar">墨</div>
              <div class="bubble typing">
                <span class="dot" /><span class="dot" /><span class="dot" />
              </div>
            </div>
          </div>

          <div class="chat-input-area">
            <el-input
              v-model="input"
              type="textarea"
              :rows="3"
              placeholder="继续对话… Enter 发送，Ctrl+Enter 也可发送"
              :disabled="!canSend"
              @keydown="onKeydown"
            />
            <el-button type="primary" :loading="sending" :disabled="!canSend || !input.trim()" @click="sendMessage">
              发送
            </el-button>
          </div>
        </section>

        <!-- 右侧文章预览 -->
        <section class="article-panel">
          <div class="panel-head">
            <span class="panel-title">文章预览</span>
            <span v-if="draft.word_count" class="word-count">{{ draft.word_count }} 字</span>
          </div>

          <div class="article-body">
            <div v-if="!draft.content" class="empty-article">
              <div class="empty-icon">📝</div>
              <p>文章将在这里实时显示</p>
              <p class="hint">与左侧 AI 对话后，成稿会自动出现在此区域</p>
            </div>

            <article v-else class="article-content">
              <h2 v-if="draft.title" class="article-title">{{ draft.title }}</h2>
              <div
                v-if="draft.html"
                class="article-html"
                v-html="draft.html"
              />
              <div
                v-else
                class="article-md"
                v-html="renderMd(draft.content)"
              />
            </article>
          </div>
        </section>
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
const draft = ref({ title: '', content: '', html: null, word_count: 0 })
const input = ref('')
const sending = ref(false)
const loadingHistory = ref(false)
const chatStatus = ref('pending')
const messagesEl = ref(null)
let pollTimer = null

const statusLabel = computed(() => {
  const map = {
    pending: '准备中',
    running: 'AI 写作中…',
    completed: '已完成',
    idle: '就绪',
    failed: '失败',
  }
  return map[chatStatus.value] || chatStatus.value
})

const statusTagType = computed(() => {
  if (chatStatus.value === 'running') return 'warning'
  if (chatStatus.value === 'completed') return 'success'
  if (chatStatus.value === 'failed') return 'danger'
  return 'info'
})

const canSend = computed(() => !sending.value && chatStatus.value !== 'running' && chatStatus.value !== 'pending')

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
  const { data } = await api.get(`/articles/work/${articleId.value}`)
  article.value = data
}

async function loadHistory() {
  if (!articleId.value) return
  loadingHistory.value = true
  try {
    const { data } = await api.get(`/articles/work/${articleId.value}/chat/history`)
    messages.value = data.messages || []
    draft.value = data.draft || { title: '', content: '', html: null, word_count: 0 }
    await nextTick()
    scrollBottom()
  } finally {
    loadingHistory.value = false
  }
}

async function pollStatus() {
  if (!articleId.value) return
  try {
    const { data } = await api.get(`/articles/work/${articleId.value}/chat/status`)
    chatStatus.value = data.status || data.work_status || 'idle'
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
  if (!input.value.trim() || !canSend.value) return
  const content = input.value.trim()
  input.value = ''
  messages.value.push({ role: 'user', content })
  await nextTick()
  scrollBottom()
  sending.value = true
  try {
    await api.post(`/articles/work/${articleId.value}/chat/send`, { content })
    chatStatus.value = 'running'
    await pollStatus()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '发送失败')
  } finally {
    sending.value = false
  }
}

function onKeydown(e) {
  if ((e.key === 'Enter' && !e.shiftKey) || (e.key === 'Enter' && e.ctrlKey)) {
    e.preventDefault()
    sendMessage()
  }
}

watch(articleId, async (id) => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (id) {
    await loadArticle()
    await pollStatus()
    pollTimer = setInterval(pollStatus, 3000)
  }
}, { immediate: true })

onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<style scoped>
.write-page {
  height: calc(100vh - 108px);
  display: flex;
  flex-direction: column;
}

.new-article {
  max-width: 700px;
  margin: 0 auto;
}

.new-article h2 { margin-bottom: 8px; }
.desc { color: #909399; margin-bottom: 24px; }

.split-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f7fa;
  border-radius: 12px;
  overflow: hidden;
}

.write-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.title-block {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.title-block h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.split-pane {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  min-height: 0;
}

.chat-panel,
.article-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #fff;
}

.chat-panel {
  border-right: 1px solid #e4e7ed;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid #ebeef5;
  background: #fafafa;
}

.panel-title {
  font-weight: 600;
  font-size: 14px;
}

.panel-hint,
.word-count {
  font-size: 12px;
  color: #909399;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #f9fafb;
}

.empty-chat,
.empty-article {
  text-align: center;
  color: #909399;
  padding: 48px 24px;
}

.empty-chat .hint,
.empty-article .hint {
  font-size: 13px;
  margin-top: 8px;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.msg-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.msg-row.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.msg-row.user .avatar {
  background: #67c23a;
}

.bubble {
  max-width: 85%;
}

.bubble-text {
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 14px;
  background: #fff;
  border: 1px solid #ebeef5;
  white-space: pre-wrap;
  word-break: break-word;
}

.msg-row.user .bubble-text {
  background: #ecf5ff;
  border-color: #d9ecff;
}

.bubble.typing {
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  display: flex;
  gap: 4px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #c0c4cc;
  animation: blink 1.2s infinite;
}

.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes blink {
  0%, 80%, 100% { opacity: 0.3; }
  40% { opacity: 1; }
}

.chat-input-area {
  padding: 12px 16px;
  border-top: 1px solid #ebeef5;
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background: #fff;
}

.chat-input-area .el-textarea {
  flex: 1;
}

.article-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.article-content {
  max-width: 720px;
  margin: 0 auto;
}

.article-title {
  font-size: 22px;
  margin: 0 0 20px;
  line-height: 1.4;
}

.article-md :deep(h1),
.article-md :deep(h2),
.article-md :deep(h3) {
  margin: 16px 0 8px;
}

.article-md :deep(p) {
  margin: 10px 0;
  line-height: 1.8;
}

.article-md :deep(hr) {
  margin: 20px 0;
  border: none;
  border-top: 1px solid #ebeef5;
}

@media (max-width: 900px) {
  .split-pane {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr 1fr;
  }
  .chat-panel {
    border-right: none;
    border-bottom: 1px solid #e4e7ed;
  }
}
</style>
