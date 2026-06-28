# Tactile Writer（墨写）

面向中国用户的 AI 文章写作平台，基于 [Tactile](https://github.com/mijunri/tactile) Agent 工作空间。

## 功能

1. **对话写作** — 与写作 Agent 实时对话，生成微信公众号、头条号等平台文章
2. **定时写作** — 配置 Cron 定时任务，每日自动撰写并归档

## 架构

```
浏览器 → tactile-writer 前端 (Vue3)
              ↓
         tactile-writer 后端 (FastAPI)
              ↓
         Tactile Gateway API (workspace / agent / work / scheduled-tasks / chat)
```

用户注册时，平台自动在 Tactile 创建账号、工作空间与写作 Agent。

## 本地开发

```bash
# 后端
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 配置 TACTILE_API_BASE
uvicorn app.main:app --reload --port 8080

# 前端
cd frontend
npm install
npm run dev
```

## 部署（阿里云杭州 ECS）

```bash
export TACTILE_API_BASE=http://118.31.57.25/tactile/api
bash scripts/deploy-ecs.sh
```

访问：`http://<ECS_IP>/writer/`

## 环境变量

| 变量 | 说明 |
|------|------|
| `TACTILE_API_BASE` | Tactile Gateway API 地址 |
| `JWT_SECRET` | 平台 JWT 密钥 |
| `DATABASE_URL` | SQLite 或 PostgreSQL 连接串 |
