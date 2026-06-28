#!/usr/bin/env python3
"""
Bootstrap 墨写基础设施到 Tactile 新加坡生产环境。

用法:
  cp infra/tactile-prod.example.env infra/tactile-prod.env
  # 编辑 MOXIE_UPLOAD_TOKEN 等
  pip install httpx
  python3 scripts/bootstrap-tactile-prod.py
"""
from __future__ import annotations

import json
import os
import zipfile
from io import BytesIO
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "infra" / "tactile-prod.env"
STATE_FILE = ROOT / "infra" / "state.json"
SKILL_DIR = ROOT / "skills" / "moxie-save-article"
SKILL_SLUG = "moxie-save-article"
SKILL_VERSION = "1.0.0"

WRITER_AGENT_INSTRUCTIONS = """你是一位专业的中文自媒体写作助手，擅长微信公众号、头条号、小红书、知乎等平台。

写作流程：
1. 根据用户要求撰写完整文章（标题 + 正文）
2. 将成稿整理为语义化 HTML（含 h1/h2/p 等标签）
3. **必须**调用 `moxie-save-article` Skill 的 `save-article.py` 上传到墨写平台存档
4. 上传成功后在对话中简要确认标题与 article_id

写作要求：
- 标题吸引人，结构清晰
- 语言通俗，适合国内读者
- 默认 800-1500 字
- 事实性内容标注「需核实」

不要跳过上传步骤；对话输出不等于已存档。"""


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def package_skill() -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in SKILL_DIR.rglob("*"):
            if fp.is_file():
                arc = fp.relative_to(SKILL_DIR).as_posix()
                zf.write(fp, arc)
    return buf.getvalue()


class Tactile:
    def __init__(self, base: str, token: str | None = None):
        self.base = base.rstrip("/")
        self.token = token
        self.client = httpx.Client(timeout=120.0)

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def request(self, method: str, path: str, **kwargs):
        url = f"{self.base}{path}"
        resp = self.client.request(method, url, headers=self._headers(), **kwargs)
        if resp.status_code >= 400:
            raise RuntimeError(f"{method} {path} -> {resp.status_code}: {resp.text}")
        return resp.json() if resp.content else None

    def register(self, email: str, password: str, display_name: str) -> str:
        data = self.request(
            "POST", "/auth/register",
            json={"email": email, "password": password, "display_name": display_name},
        )
        return data["access_token"]

    def login(self, email: str, password: str) -> str:
        data = self.request("POST", "/auth/login", json={"email": email, "password": password})
        return data["access_token"]

    def upload_skill(self, workspace_id: int, slug: str, name: str, version: str, package: bytes):
        url = f"{self.base}/skill-plaza/upload"
        files = {"package": (f"{slug}.zip", package, "application/zip")}
        data = {
            "slug": slug,
            "name": name,
            "version": version,
            "description": "Save article HTML to Moxie platform",
            "changelog": "initial",
            "workspace_id": str(workspace_id),
            "category": "content",
        }
        resp = self.client.post(
            url,
            headers={"Authorization": f"Bearer {self.token}"},
            data=data,
            files=files,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"upload skill -> {resp.status_code}: {resp.text}")
        return resp.json()


def main() -> None:
    if not ENV_FILE.exists():
        raise SystemExit(f"Missing {ENV_FILE}. Copy from infra/tactile-prod.example.env")

    env = load_env(ENV_FILE)
    base = env["TACTILE_API_BASE"]
    email = env["TACTILE_SERVICE_EMAIL"]
    password = env["TACTILE_SERVICE_PASSWORD"]
    display = env.get("TACTILE_SERVICE_DISPLAY_NAME", "墨写服务")
    ws_name = env.get("TACTILE_WORKSPACE_NAME", "墨写空间")
    agent_name = env.get("TACTILE_AGENT_NAME", "通用写作助手")
    moxie_api = env.get("MOXIE_API_BASE", "")
    moxie_token = env.get("MOXIE_UPLOAD_TOKEN", "")

    api = Tactile(base)
    try:
        token = api.register(email, password, display)
        print(f"Registered {email}")
    except RuntimeError as e:
        if "already" in str(e).lower() or "400" in str(e):
            token = api.login(email, password)
            print(f"Logged in {email}")
        else:
            raise
    api.token = token

    workspaces = api.request("GET", "/workspace")
    workspace = next((w for w in workspaces if w.get("name") == ws_name), None)
    if not workspace:
        workspace = next((w for w in workspaces if w.get("workspace_scope") == 0), None)
    if not workspace:
        try:
            workspace = api.request(
                "POST", "/workspace", json={"name": ws_name, "description": "墨写平台生产空间"}
            )
            print(f"Created workspace id={workspace['id']}")
        except RuntimeError as e:
            if "409" in str(e) or "already" in str(e).lower():
                workspaces = api.request("GET", "/workspace")
                workspace = workspaces[0] if workspaces else None
            else:
                raise
    if workspace:
        print(f"Using workspace id={workspace['id']} name={workspace.get('name')}")
    else:
        raise RuntimeError("No workspace available")
    ws_id = workspace["id"]

    # Upload skill
    pkg = package_skill()
    try:
        skill = api.upload_skill(ws_id, SKILL_SLUG, "墨写文章保存", SKILL_VERSION, pkg)
        print(f"Uploaded skill id={skill['id']} slug={SKILL_SLUG}")
    except RuntimeError as e:
        if "already" in str(e).lower() or "409" in str(e) or "exist" in str(e).lower():
            skills = api.request("GET", "/skill-plaza/manage", params={"workspace_id": ws_id})
            skill = next((s for s in skills.get("items", []) if s.get("slug") == SKILL_SLUG), None)
            if not skill:
                market = api.request("GET", "/skill-plaza", params={"search": SKILL_SLUG})
                skill = next((s for s in market.get("items", []) if s.get("slug") == SKILL_SLUG), None)
            print(f"Skill exists id={skill['id'] if skill else '?'}")
        else:
            raise
    skill_id = skill["id"]
    version_id = skill.get("latest_version_id") or skill.get("version_id")
    if not version_id and skill.get("versions"):
        version_id = skill["versions"][0]["id"]

    # Install skill to workspace if needed
    try:
        api.request(
            "POST", f"/skill-plaza/{skill_id}/install",
            json={"workspace_id": ws_id, "slug": SKILL_SLUG},
        )
        print("Installed skill to workspace")
    except RuntimeError:
        pass

    # Create or get agent
    agents = api.request("GET", "/agent", params={"workspace_id": ws_id})
    agent = next((a for a in agents if a.get("name") == agent_name), None)
    if not agent:
        agent = api.request(
            "POST", "/agent",
            json={
                "workspace_id": ws_id,
                "name": agent_name,
                "description": "墨写通用写作 Agent，成稿后通过 moxie-save-article 上传",
                "instructions": WRITER_AGENT_INSTRUCTIONS,
                "runtime_type": "ecs",
            },
        )
        print(f"Created agent id={agent['id']}")
    else:
        api.request(
            "PUT", f"/agent/{agent['id']}",
            json={"instructions": WRITER_AGENT_INSTRUCTIONS, "runtime_type": "ecs"},
        )
        print(f"Updated agent id={agent['id']}")
    agent_id = agent["id"]

    # Bind skill to agent
    if version_id:
        api.request(
            "PUT", f"/agent/{agent_id}/bindings",
            json={"skills": [{"skill_id": skill_id, "version_id": version_id}]},
        )
        print("Bound skill to agent")

    # Agent env vars for skill
    api.request(
        "PUT", f"/agent/{agent_id}/env-vars",
        json={
            "items": [
                {"env_key": "MOXIE_API_BASE", "env_value": moxie_api, "enabled": True},
                {"env_key": "MOXIE_UPLOAD_TOKEN", "env_value": moxie_token, "enabled": True},
            ]
        },
    )
    print("Set agent env vars")

    state = {
        "tactile_api_base": base,
        "service_email": email,
        "workspace_id": ws_id,
        "workspace_name": ws_name,
        "agent_id": agent_id,
        "agent_name": agent_name,
        "skill_id": skill_id,
        "skill_slug": SKILL_SLUG,
        "skill_version": SKILL_VERSION,
        "moxie_api_base": moxie_api,
    }
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nState written to {STATE_FILE}")
    print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
