from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import PlatformUser, SavedArticle
from app.schemas import (
    ArticleCreate,
    ArticleDraft,
    ArticleResponse,
    ArticleUploadRequest,
    ChatHistoryResponse,
    ChatMessage,
    ChatSendRequest,
    SavedArticleListItem,
    SavedArticleResponse,
)
from app.services.chat_parser import build_chat_display, extract_article_draft, parse_tactile_history
from app.services.tactile_service import get_agent_id, get_service_client, get_workspace_id
from app.tactile_client import TactileAPIError

router = APIRouter(prefix="/api/articles", tags=["articles"])
internal_router = APIRouter(prefix="/api/internal/articles", tags=["internal"])


def _parse_work(item: dict) -> ArticleResponse:
    return ArticleResponse(
        id=item["id"],
        name=item.get("name", ""),
        status=item.get("status", ""),
        sandbox_status=item.get("sandbox_status"),
        session_id=item.get("session_id"),
        content=item.get("content"),
        create_time=item.get("create_time"),
    )


@router.get("/saved", response_model=list[SavedArticleListItem])
async def list_saved(
    db: AsyncSession = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user),
):
    _ = current_user
    result = await db.execute(select(SavedArticle).order_by(SavedArticle.create_time.desc()))
    rows = result.scalars().all()
    return [
        SavedArticleListItem(
            id=r.id,
            title=r.title,
            platform=r.platform,
            work_item_id=r.work_item_id,
            create_time=r.create_time,
        )
        for r in rows
    ]


@router.get("/saved/{article_id}", response_model=SavedArticleResponse)
async def get_saved(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user),
):
    _ = current_user
    result = await db.execute(select(SavedArticle).where(SavedArticle.id == article_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="文章不存在")
    return SavedArticleResponse(
        id=row.id,
        title=row.title,
        platform=row.platform,
        html_content=row.html_content,
        work_item_id=row.work_item_id,
        create_time=row.create_time,
    )


@router.get("/in-progress", response_model=list[ArticleResponse])
async def list_in_progress(current_user: PlatformUser = Depends(get_current_user)):
    _ = current_user
    client = await get_service_client()
    try:
        items = await client.list_work_items(get_workspace_id())
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return [_parse_work(i) for i in items]


@router.post("", response_model=ArticleResponse)
async def create_article(
    data: ArticleCreate,
    current_user: PlatformUser = Depends(get_current_user),
):
    _ = current_user
    client = await get_service_client()
    prompt = (
        f"请为【{data.platform}】撰写一篇文章。\n\n"
        f"主题/要求：{data.topic}\n\n"
        "请直接输出文章内容（Markdown 格式），语气符合该平台读者习惯。"
    )
    try:
        item = await client.create_work_item(
            get_workspace_id(), get_agent_id(), prompt, data.name
        )
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return _parse_work(item)


@router.get("/work/{work_id}", response_model=ArticleResponse)
async def get_work(work_id: int, current_user: PlatformUser = Depends(get_current_user)):
    _ = current_user
    client = await get_service_client()
    try:
        item = await client.get_work_item(work_id)
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return _parse_work(item)


@router.post("/work/{work_id}/chat/send")
async def send_message(
    work_id: int,
    data: ChatSendRequest,
    current_user: PlatformUser = Depends(get_current_user),
):
    _ = current_user
    client = await get_service_client()
    try:
        item = await client.get_work_item(work_id)
        session_id = item.get("session_id")
        if not session_id:
            raise HTTPException(status_code=400, detail="文章会话未就绪，请稍候")
        return await client.send_chat(session_id, data.content)
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)


@router.get("/work/{work_id}/chat/history", response_model=ChatHistoryResponse)
async def chat_history(work_id: int, current_user: PlatformUser = Depends(get_current_user)):
    _ = current_user
    client = await get_service_client()
    try:
        item = await client.get_work_item(work_id)
        session_id = item.get("session_id")
        if not session_id:
            return ChatHistoryResponse(messages=[], draft=ArticleDraft())
        history = await client.get_chat_history(session_id, rounds=50)
        parsed = parse_tactile_history(history)
        draft_data = extract_article_draft(parsed, title=item.get("name", ""))
        display = build_chat_display(parsed, draft_data["content"])
        return ChatHistoryResponse(
            messages=[ChatMessage(**m) for m in display],
            draft=ArticleDraft(**draft_data),
        )
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)


@router.get("/work/{work_id}/chat/status")
async def chat_status(work_id: int, current_user: PlatformUser = Depends(get_current_user)):
    _ = current_user
    client = await get_service_client()
    try:
        item = await client.get_work_item(work_id)
        session_id = item.get("session_id")
        work_status = item.get("status", "pending")
        sandbox_status = item.get("sandbox_status")

        if not session_id:
            return {
                "status": "pending",
                "work_status": work_status,
                "sandbox_status": sandbox_status,
            }

        status = await client.get_chat_status(session_id)
        if status.get("processing"):
            chat_status = "running"
        elif work_status in ("failed",):
            chat_status = "failed"
        elif work_status in ("idle",) and status.get("prepared"):
            chat_status = "completed"
        elif work_status in ("running", "scheduled", "pending"):
            chat_status = "running"
        else:
            chat_status = "idle"

        return {
            **status,
            "status": chat_status,
            "work_status": work_status,
            "sandbox_status": sandbox_status,
        }
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)


@internal_router.post("/upload")
async def upload_article(
    data: ArticleUploadRequest,
    x_moxie_token: str | None = Header(default=None, alias="X-Moxie-Token"),
    db: AsyncSession = Depends(get_db),
):
    if not x_moxie_token or x_moxie_token != settings.moxie_upload_token:
        raise HTTPException(status_code=401, detail="Invalid upload token")
    row = SavedArticle(
        title=data.title,
        platform=data.platform,
        html_content=data.html,
        work_item_id=data.work_item_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"ok": True, "article_id": row.id, "title": row.title}
