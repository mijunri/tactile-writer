from typing import Any

import httpx

from app.config import settings


class TactileAPIError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(detail)


class TactileClient:
    def __init__(self, token: str | None = None):
        self.base = settings.tactile_api_base.rstrip("/")
        self.token = token

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _request(
        self, method: str, path: str, *, json: dict | None = None, params: dict | None = None
    ) -> Any:
        url = f"{self.base}{path}"
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.request(
                method, url, headers=self._headers(), json=json, params=params
            )
        if resp.status_code >= 400:
            detail = resp.text
            try:
                detail = resp.json().get("detail", detail)
            except Exception:
                pass
            raise TactileAPIError(resp.status_code, str(detail))
        if resp.status_code == 204:
            return None
        return resp.json()

    async def register(self, email: str, password: str, display_name: str) -> dict:
        return await self._request(
            "POST",
            "/auth/register",
            json={"email": email, "password": password, "display_name": display_name},
        )

    async def login(self, email: str, password: str) -> dict:
        return await self._request(
            "POST", "/auth/login", json={"email": email, "password": password}
        )

    async def list_workspaces(self) -> list[dict]:
        return await self._request("GET", "/workspace")

    async def create_workspace(self, name: str, description: str = "") -> dict:
        return await self._request(
            "POST", "/workspace", json={"name": name, "description": description}
        )

    async def create_agent(
        self, workspace_id: int, name: str, instructions: str, description: str = ""
    ) -> dict:
        return await self._request(
            "POST",
            "/agent",
            json={
                "workspace_id": workspace_id,
                "name": name,
                "description": description,
                "instructions": instructions,
                "runtime_type": "sandbox",
            },
        )

    async def list_agents(self, workspace_id: int) -> list[dict]:
        return await self._request("GET", "/agent", params={"workspace_id": workspace_id})

    async def create_work_item(
        self,
        workspace_id: int,
        agent_id: int,
        content: str,
        name: str = "新文章",
        *,
        machine_type: str = "ubuntu",
    ) -> dict:
        return await self._request(
            "POST",
            "/work",
            json={
                "workspace_id": workspace_id,
                "agent_id": agent_id,
                "content": content,
                "name": name,
                "machine_type": machine_type,
            },
        )

    async def list_work_items(self, workspace_id: int) -> list[dict]:
        return await self._request("GET", "/work", params={"workspace_id": workspace_id})

    async def get_work_item(self, work_id: int) -> dict:
        return await self._request("GET", f"/work/{work_id}")

    async def send_chat(self, session_id: str, content: str) -> dict:
        return await self._request(
            "POST", f"/chat/{session_id}/send", json={"content": content}
        )

    async def get_chat_history(self, session_id: str, rounds: int = 20) -> dict:
        return await self._request(
            "GET", f"/chat/{session_id}/history", params={"rounds": rounds}
        )

    async def get_chat_status(self, session_id: str) -> dict:
        return await self._request("GET", f"/chat/{session_id}/status")

    async def list_scheduled_tasks(self, workspace_id: int) -> list[dict]:
        return await self._request("GET", f"/workspace/{workspace_id}/scheduled-tasks")

    async def create_scheduled_task(self, workspace_id: int, data: dict) -> dict:
        return await self._request(
            "POST", f"/workspace/{workspace_id}/scheduled-tasks", json=data
        )

    async def toggle_scheduled_task(
        self, workspace_id: int, task_id: int, enabled: bool
    ) -> dict:
        return await self._request(
            "POST",
            f"/workspace/{workspace_id}/scheduled-tasks/{task_id}/toggle",
            json={"enabled": enabled},
        )

    async def delete_scheduled_task(self, workspace_id: int, task_id: int) -> None:
        await self._request(
            "DELETE", f"/workspace/{workspace_id}/scheduled-tasks/{task_id}"
        )

    async def trigger_scheduled_task(self, workspace_id: int, task_id: int) -> dict:
        return await self._request(
            "POST", f"/workspace/{workspace_id}/scheduled-tasks/{task_id}/trigger"
        )

    async def get_run_history(
        self, workspace_id: int, task_id: int, limit: int = 20
    ) -> dict:
        return await self._request(
            "GET",
            f"/workspace/{workspace_id}/scheduled-tasks/{task_id}/run-history",
            params={"limit": limit},
        )
