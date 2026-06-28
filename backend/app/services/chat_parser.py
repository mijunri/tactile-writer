"""Parse Tactile chat history API into user/assistant messages and article draft."""
from __future__ import annotations

import re
from typing import Any


def _merge_chunks(messages: list[dict]) -> list[dict]:
    merged: list[dict] = []
    for msg in messages:
        mtype = msg.get("message_type", "")
        mid = msg.get("message_id")
        if merged and mtype in ("CHUNK", "UPDATE") and merged[-1].get("message_id") == mid:
            prev = merged[-1]
            prev["content"] = (prev.get("content") or "") + (msg.get("content") or "")
        else:
            merged.append(dict(msg))
    return merged


def _is_noise(content: str) -> bool:
    if not content:
        return True
    if content.startswith("[Claude Code via ACP"):
        return True
    if content.startswith("(Set E2B_DOMAIN"):
        return True
    if content.startswith("User:"):
        return True
    return False


def parse_tactile_history(history: dict | list) -> list[dict[str, Any]]:
    raw = history.get("messages", []) if isinstance(history, dict) else history
    if not raw:
        return []

    merged = _merge_chunks(raw)
    result: list[dict[str, Any]] = []

    for msg in merged:
        mtype = msg.get("message_type", "")
        content = (msg.get("content") or "").strip()
        if mtype == "DONE" or _is_noise(content):
            continue

        if mtype == "USER_MESSAGE":
            result.append({"role": "user", "content": content, "index": msg.get("entry_index")})
            continue

        if mtype in ("CHUNK", "UPDATE", "ASSISTANT_MESSAGE"):
            result.append({"role": "assistant", "content": content, "index": msg.get("entry_index")})

    return result


def _strip_meta(text: str) -> str:
    text = re.sub(r"\(Set E2B_DOMAIN.*?\)\s*", "", text)
    text = re.sub(r"\[Claude Code via ACP[^\]]*\]\s*", "", text)
    return text.strip()


def _extract_html(text: str) -> str | None:
    match = re.search(r"(<html[\s\S]*?</html>|<article[\s\S]*?</article>)", text, re.I)
    if match:
        return match.group(1)
    if re.search(r"<h[1-6][\s\S]*</p>", text, re.I):
        return text
    return None


def extract_article_draft(messages: list[dict[str, Any]], title: str = "") -> dict[str, Any]:
    assistant_parts = [
        _strip_meta(m["content"])
        for m in messages
        if m.get("role") == "assistant" and m.get("content") and not _is_noise(m["content"])
    ]
    content = ""
    if assistant_parts:
        content = max(assistant_parts, key=len).strip()

    html = _extract_html(content) if content else None
    plain = re.sub(r"<[^>]+>", "", content) if html else content
    word_count = len(re.sub(r"\s+", "", plain)) if plain else 0

    draft_title = title
    if not draft_title and content:
        for line in content.splitlines():
            line = line.strip().lstrip("#").strip()
            if line and len(line) < 80:
                draft_title = line
                break

    return {
        "title": draft_title or "未命名文章",
        "content": content,
        "html": html,
        "word_count": word_count,
    }


def build_chat_display(messages: list[dict[str, Any]], draft_content: str) -> list[dict[str, Any]]:
    """Chat panel: shorten long assistant replies that are the article body."""
    display: list[dict[str, Any]] = []
    draft_norm = draft_content.strip()

    for msg in messages:
        role = msg.get("role", "assistant")
        content = (msg.get("content") or "").strip()
        if role == "user":
            display.append({"role": "user", "content": content, "index": msg.get("index")})
            continue

        if draft_norm and content.strip() == draft_norm:
            display.append(
                {
                    "role": "assistant",
                    "content": "✓ 文章草稿已更新，请在右侧预览",
                    "index": msg.get("index"),
                }
            )
        elif len(content) > 300:
            display.append(
                {
                    "role": "assistant",
                    "content": "✓ 已生成内容，请在右侧预览文章",
                    "index": msg.get("index"),
                }
            )
        else:
            display.append({"role": "assistant", "content": content, "index": msg.get("index")})

    return display
