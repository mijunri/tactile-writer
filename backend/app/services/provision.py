from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import WRITER_AGENT_INSTRUCTIONS, WRITER_AGENT_NAME, WRITER_WORKSPACE_NAME
from app.models import PlatformUser
from app.tactile_client import TactileAPIError, TactileClient


async def provision_tactile_resources(
    db: AsyncSession, user: PlatformUser, email: str, password: str, display_name: str
) -> None:
    """Register on Tactile and create workspace + writer agent."""
    client = TactileClient()
    try:
        auth = await client.register(email, password, display_name or email.split("@")[0])
    except TactileAPIError as e:
        if e.status == 400 and "already" in e.detail.lower():
            auth = await client.login(email, password)
        else:
            raise

    token = auth["access_token"]
    user.tactile_token = token
    tactile_client = TactileClient(token)

    workspaces = await tactile_client.list_workspaces()
    workspace = None
    for ws in workspaces:
        if ws.get("name") == WRITER_WORKSPACE_NAME or ws.get("workspace_scope") == 0:
            workspace = ws
            break

    if not workspace:
        workspace = await tactile_client.create_workspace(
            WRITER_WORKSPACE_NAME, "墨写平台自动创建的文章写作空间"
        )

    user.tactile_workspace_id = workspace["id"]

    agents = await tactile_client.list_agents(workspace["id"])
    writer_agent = next((a for a in agents if a.get("name") == WRITER_AGENT_NAME), None)
    if not writer_agent:
        writer_agent = await tactile_client.create_agent(
            workspace["id"],
            WRITER_AGENT_NAME,
            WRITER_AGENT_INSTRUCTIONS,
            "专业中文自媒体写作助手",
        )

    user.tactile_agent_id = writer_agent["id"]
    await db.commit()


def get_tactile_client(user: PlatformUser) -> TactileClient:
    if not user.tactile_token:
        raise ValueError("Tactile not provisioned")
    return TactileClient(user.tactile_token)
