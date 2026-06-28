---
name: moxie-save-article
description: >
  将写好的文章保存为 HTML 并上传到墨写平台。文章写作完成后必须调用本 Skill，
  把标题、平台、正文 HTML 提交到墨写后端存储。Use after finishing any article writing task.
category: content
tags: moxie, article, upload, html, writer
---

# 墨写 — 文章保存

写作任务**完成后**，必须把成稿上传到墨写平台存档。

## 环境变量

| 变量 | 说明 |
|------|------|
| `MOXIE_API_BASE` | 墨写 API，如 `http://118.31.57.25/writer/api` |
| `MOXIE_UPLOAD_TOKEN` | 上传鉴权 token |

## 何时使用

- 文章正文已全部写好（含标题）
- 用户要求保存、发布、存档
- 定时写作任务结束前的最后一步

## 操作步骤

1. 将文章整理为**完整 HTML**（含 `<html>`、`<head>`、`<body>`，正文用语义化标签）
2. 执行上传脚本：

```bash
python3 scripts/save-article.py \
  --title "文章标题" \
  --platform "微信公众号" \
  --html-file /path/to/article.html
```

或从 stdin 传入 HTML：

```bash
python3 scripts/save-article.py \
  --title "文章标题" \
  --platform "头条号" \
  --html-stdin < article.html
```

3. 确认脚本返回 `{"ok": true, "article_id": ...}`

## HTML 要求

- 必须包含 `<h1>` 作为文章标题（与 `--title` 一致）
- 正文用 `<p>`、`<h2>`、`<ul>` 等标签
- 不要外链脚本；样式用内联或 `<style>` 块
- 中文 UTF-8 编码

## 注意

- **每次写完必调用**，不要只在对话里输出而不上传
- `work_item_id` 可选，有则传入 `--work-item-id` 便于关联任务
