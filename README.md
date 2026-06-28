# Tactile Writer（墨写）

面向中国用户的 AI 文章写作平台，底层基础设施为 **Tactile 新加坡生产环境**（`https://cloudagentlab.com`）。

## 架构

```
墨写前端/后端 (杭州 ECS)
        ↓ 写作任务
Tactile 新加坡生产 API (cloudagentlab.com)
        ↓ ECS Worker + Claude Code
通用写作 Agent + moxie-save-article Skill
        ↓ 成稿 HTML 上传
墨写后端 /api/internal/articles/upload → 本地存档展示
```

## 基础设施初始化（一次性）

```bash
cp infra/tactile-prod.example.env infra/tactile-prod.env
# 编辑 MOXIE_UPLOAD_TOKEN 等
pip install httpx
python3 scripts/bootstrap-tactile-prod.py
# 生成 infra/state.json（workspace_id / agent_id / skill_id）
```

### 生产账号（定义在 `infra/tactile-prod.example.env`）

| 项 | 值 |
|----|-----|
| Tactile API | `https://cloudagentlab.com/api` |
| 服务邮箱 | `moxie-writer@imjson.cn` |
| 工作空间 | 墨写空间（bootstrap 后见 state.json） |
| Agent | 通用写作助手 |
| Skill | `moxie-save-article`（写完 HTML 上传墨写） |

## 访问

- **http://118.31.57.25/writer/**

## 部署

```bash
bash scripts/deploy-ecs.sh
```

## Skill：moxie-save-article

Agent 写完文章后执行：

```bash
python3 scripts/save-article.py --title "标题" --platform "微信公众号" --html-file article.html
```

环境变量：`MOXIE_API_BASE`、`MOXIE_UPLOAD_TOKEN`（由 Agent env 注入）
