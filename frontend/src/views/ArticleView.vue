<template>
  <div class="article-view" v-loading="loading">
    <div class="header">
      <el-button text @click="$router.push('/')">← 返回</el-button>
      <h2>{{ article?.title }}</h2>
      <el-tag>{{ article?.platform }}</el-tag>
    </div>
    <el-card>
      <div class="html-body" v-html="article?.html_content"></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api/client'

const route = useRoute()
const article = ref(null)
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await api.get(`/articles/saved/${route.params.id}`)
    article.value = data
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.html-body { line-height: 1.8; font-size: 15px; }
.html-body :deep(h1) { font-size: 24px; margin-bottom: 16px; }
.html-body :deep(h2) { font-size: 18px; margin: 16px 0 8px; }
.html-body :deep(p) { margin: 8px 0; }
</style>
