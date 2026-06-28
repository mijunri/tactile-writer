from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_current_user
from app.models import PlatformUser
from app.schemas import ScheduleCreate, ScheduleResponse, ScheduleToggle
from app.services.tactile_service import get_agent_id, get_service_client, get_workspace_id
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
    _ = current_user
    client = await get_service_client()
    try:
        items = await client.list_scheduled_tasks(get_workspace_id())
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return [_parse_schedule(i) for i in items]


@router.post("", response_model=ScheduleResponse)
async def create_schedule(data: ScheduleCreate, current_user: PlatformUser = Depends(get_current_user)):
    _ = current_user
    client = await get_service_client()
    prompt = (
        f"【定时写作 - {data.platform}】\n\n{data.prompt_template}\n\n"
        "写完后整理 HTML，调用 moxie-save-article Skill 上传墨写。"
    )
    try:
        item = await client.create_scheduled_task(
            get_workspace_id(),
            {
                "name": data.name,
                "trigger_type": "cron",
                "cron_expression": data.cron_expression,
                "prompt_template": prompt,
                "agent_id": get_agent_id(),
                "archive_on_complete": True,
            },
        )
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return _parse_schedule(item)


@router.post("/{task_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule(
    task_id: int, data: ScheduleToggle, current_user: PlatformUser = Depends(get_current_user)
):
    _ = current_user
    client = await get_service_client()
    try:
        item = await client.toggle_scheduled_task(get_workspace_id(), task_id, data.enabled)
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return _parse_schedule(item)


@router.post("/{task_id}/trigger")
async def trigger_schedule(task_id: int, current_user: PlatformUser = Depends(get_current_user)):
    _ = current_user
    client = await get_service_client()
    try:
        return await client.trigger_scheduled_task(get_workspace_id(), task_id)
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)


@router.delete("/{task_id}")
async def delete_schedule(task_id: int, current_user: PlatformUser = Depends(get_current_user)):
    _ = current_user
    client = await get_service_client()
    try:
        await client.delete_scheduled_task(get_workspace_id(), task_id)
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return {"ok": True}


@router.get("/{task_id}/runs")
async def schedule_runs(task_id: int, current_user: PlatformUser = Depends(get_current_user)):
    _ = current_user
    client = await get_service_client()
    try:
        return await client.get_run_history(get_workspace_id(), task_id)
    except TactileAPIError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
