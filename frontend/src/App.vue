<template>
  <el-container class="app-layout">
    <el-header v-if="showNav" class="app-header">
      <div class="brand" @click="$router.push('/')">
        <span class="logo">墨</span>
        <span class="title">墨写</span>
        <span class="subtitle">AI 文章写作</span>
      </div>
      <el-menu mode="horizontal" :ellipsis="false" router :default-active="activeRoute">
        <el-menu-item index="/">文章列表</el-menu-item>
        <el-menu-item index="/write">对话写作</el-menu-item>
        <el-menu-item index="/schedules">定时任务</el-menu-item>
      </el-menu>
      <div class="user-area">
        <el-button text @click="logout">退出</el-button>
      </div>
    </el-header>
    <el-main :class="{ 'no-header': !showNav }">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const showNav = computed(() => route.name !== 'login')
const activeRoute = computed(() => {
  if (route.path.startsWith('/write')) return '/write'
  return route.path
})

function logout() {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  background: #f5f7fa;
  color: #303133;
}
.app-layout { min-height: 100vh; }
.app-header {
  display: flex;
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  padding: 0 24px;
  height: 60px !important;
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  margin-right: 32px;
  flex-shrink: 0;
}
.logo {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #409eff, #67c23a);
  color: #fff;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
}
.title { font-size: 18px; font-weight: 600; }
.subtitle { font-size: 12px; color: #909399; }
.el-main { padding: 24px; max-width: 1200px; margin: 0 auto; width: 100%; }
.el-main.no-header { max-width: none; padding: 0; }
.user-area { margin-left: auto; }
</style>
