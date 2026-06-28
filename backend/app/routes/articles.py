from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import PlatformUser
from app.schemas import ArticleCreate, ArticleResponse, ChatMessage, ChatSendRequest
from app.services.provision import get_tactile_client
from app.tactile_client import TactileAPIError

router = APIRouter(prefix="/api/articles", tags=["articles"])


def _parse_article(item: dict) -> ArticleResponse:
    return ArticleResponse(
        id=item["id"],
        name=item.get("name", ""),
        status=item.get("status", ""),
        sandbox_status=item.get("sandbox_status"),
        session_id=item.get("session_id"),
        content=item.get("content"),
        create_time=item.get("create_time"),
    )


@router.get("", response_model=list[ArticleResponse])
async def list_articles(current_user: PlatformUser = Depends(get_current_user)):
    client = get_tactile_client(current_user)
    try:
        items = await client.list_work_items(current_user.tactile_workspace_id)
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return [_parse_article(i) for i in items]


@router.post("", response_model=ArticleResponse)
async def create_article(
    data: ArticleCreate,
    current_user: PlatformUser = Depends(get_current_user),
):
    client = get_tactile_client(current_user)
    prompt = (
        f"请为【{data.platform}】撰写一篇文章。\n\n"
        f"主题/要求：{data.topic}\n\n"
        "请直接输出完整文章（含标题），Markdown 格式。"
    )
    try:
        item = await client.create_work_item(
            current_user.tactile_workspace_id,
            current_user.tactile_agent_id,
            prompt,
            data.name,
        )
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return _parse_article(item)


@router.get("/{work_id}", response_model=ArticleResponse)
async def get_article(work_id: int, current_user: PlatformUser = Depends(get_current_user)):
    client = get_tactile_client(current_user)
    try:
        item = await client.get_work_item(work_id)
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return _parse_article(item)


@router.post("/{work_id}/chat/send")
async def send_message(
    work_id: int,
    data: ChatSendRequest,
    current_user: PlatformUser = Depends(get_current_user),
):
    client = get_tactile_client(current_user)
    try:
        item = await client.get_work_item(work_id)
        session_id = item.get("session_id")
        if not session_id:
            raise HTTPException(status_code=400, detail="文章会话未就绪，请稍候")
        result = await client.send_chat(session_id, data.content)
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return result


@router.get("/{work_id}/chat/history", response_model=list[ChatMessage])
async def chat_history(
    work_id: int,
    current_user: PlatformUser = Depends(get_current_user),
):
    client = get_tactile_client(current_user)
    try:
        item = await client.get_work_item(work_id)
        session_id = item.get("session_id")
        if not session_id:
            return []
        history = await client.get_chat_history(session_id, rounds=50)
        messages = []
        for msg in history.get("messages", []):
            messages.append(
                ChatMessage(
                    role=msg.get("role", "assistant"),
                    content=msg.get("content", ""),
                    index=msg.get("index"),
                )
            )
        return messages
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)


@router.get("/{work_id}/chat/status")
async def chat_status(work_id: int, current_user: PlatformUser = Depends(get_current_user)):
    client = get_tactile_client(current_user)
    try:
        item = await client.get_work_item(work_id)
        session_id = item.get("session_id")
        if not session_id:
            return {"status": "pending", "sandbox_status": item.get("sandbox_status")}
        status = await client.get_chat_status(session_id)
        return {**status, "work_status": item.get("status"), "sandbox_status": item.get("sandbox_status")}
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
