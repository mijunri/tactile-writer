from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    display_name: str = Field(default="", max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    email: str
    display_name: str
    workspace_id: int | None = None
    agent_id: int | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    workspace_id: int | None
    agent_id: int | None
    create_time: datetime


class ArticleCreate(BaseModel):
    topic: str = Field(min_length=1, max_length=2000)
    platform: str = Field(default="微信公众号", max_length=50)
    name: str = Field(default="新文章", max_length=200)


class ArticleResponse(BaseModel):
    id: int
    name: str
    status: str
    sandbox_status: str | None = None
    session_id: str | None = None
    content: str | None = None
    create_time: datetime | None = None


class ChatSendRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class ChatMessage(BaseModel):
    role: str
    content: str
    index: int | None = None


class ScheduleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    cron_expression: str = Field(description="Cron 表达式，如 0 8 * * *")
    prompt_template: str = Field(min_length=1)
    platform: str = Field(default="微信公众号", max_length=50)


class ScheduleResponse(BaseModel):
    id: int
    name: str
    cron_expression: str | None
    prompt_template: str
    enabled: bool
    agent_id: int | None = None
    create_time: datetime | None = None


class ScheduleToggle(BaseModel):
    enabled: bool
