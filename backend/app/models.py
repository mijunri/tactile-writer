from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PlatformUser(Base):
    __tablename__ = "platform_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(100), default="")
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class SavedArticle(Base):
    __tablename__ = "saved_article"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500))
    platform: Mapped[str] = mapped_column(String(100), default="微信公众号")
    html_content: Mapped[str] = mapped_column(Text)
    work_item_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    creator_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
