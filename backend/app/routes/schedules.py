from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_current_user
from app.models import PlatformUser
from app.schemas import ScheduleCreate, ScheduleResponse, ScheduleToggle
from app.services.provision import get_tactile_client
from app.tactile_client import TactileAPIError

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


def _parse_schedule(item: dict) -> ScheduleResponse:
    return ScheduleResponse(
        id=item["id"],
        name=item.get("name", ""),
        cron_expression=item.get("cron_expression"),
        prompt_template=item.get("prompt_template", ""),
        enabled=item.get("enabled", False),
        agent_id=item.get("agent_id"),
        create_time=item.get("create_time"),
    )


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(current_user: PlatformUser = Depends(get_current_user)):
    client = get_tactile_client(current_user)
    try:
        items = await client.list_scheduled_tasks(current_user.tactile_workspace_id)
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return [_parse_schedule(i) for i in items]


@router.post("", response_model=ScheduleResponse)
async def create_schedule(
    data: ScheduleCreate,
    current_user: PlatformUser = Depends(get_current_user),
):
    client = get_tactile_client(current_user)
    prompt = (
        f"【定时写作任务 - {data.platform}】\n\n"
        f"{data.prompt_template}\n\n"
        "请直接输出完整文章（含标题），Markdown 格式，无需与用户确认。"
    )
    try:
        item = await client.create_scheduled_task(
            current_user.tactile_workspace_id,
            {
                "name": data.name,
                "trigger_type": "cron",
                "cron_expression": data.cron_expression,
                "prompt_template": prompt,
                "agent_id": current_user.tactile_agent_id,
                "archive_on_complete": True,
            },
        )
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return _parse_schedule(item)


@router.post("/{task_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule(
    task_id: int,
    data: ScheduleToggle,
    current_user: PlatformUser = Depends(get_current_user),
):
    client = get_tactile_client(current_user)
    try:
        item = await client.toggle_scheduled_task(
            current_user.tactile_workspace_id, task_id, data.enabled
        )
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return _parse_schedule(item)


@router.post("/{task_id}/trigger")
async def trigger_schedule(task_id: int, current_user: PlatformUser = Depends(get_current_user)):
    client = get_tactile_client(current_user)
    try:
        result = await client.trigger_scheduled_task(
            current_user.tactile_workspace_id, task_id
        )
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return result


@router.delete("/{task_id}")
async def delete_schedule(task_id: int, current_user: PlatformUser = Depends(get_current_user)):
    client = get_tactile_client(current_user)
    try:
        await client.delete_scheduled_task(current_user.tactile_workspace_id, task_id)
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return {"ok": True}


@router.get("/{task_id}/runs")
async def schedule_runs(task_id: int, current_user: PlatformUser = Depends(get_current_user)):
    client = get_tactile_client(current_user)
    try:
        return await client.get_run_history(current_user.tactile_workspace_id, task_id)
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
