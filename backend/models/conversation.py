from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel


@dataclass
class Conversation:
    """对话元数据数据类"""
    id: UUID
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    is_active: bool


@dataclass
class Message:
    """单条消息数据类"""
    id: UUID
    conversation_id: UUID
    role: str  # 'user' or 'model'
    content: str
    created_at: datetime


# Pydantic schemas for API
class ConversationListItem(BaseModel):
    """对话列表项响应模式"""
    id: str
    title: str
    updated_at: str
    is_active: bool


class ConversationListResponse(BaseModel):
    """对话列表响应"""
    conversations: List[ConversationListItem]


class ConversationDetailResponse(BaseModel):
    """对话详情响应（包含所有消息）"""
    id: str
    title: str
    messages: List[dict]


class CreateConversationRequest(BaseModel):
    """创建对话请求"""
    title: Optional[str] = None


class CreateConversationResponse(BaseModel):
    """创建对话响应"""
    id: str
    title: str


class AddMessageRequest(BaseModel):
    """添加消息到对话请求"""
    role: str
    content: str


class AddMessageResponse(BaseModel):
    """添加消息响应"""
    success: bool
    message_id: str


class UpdateConversationTitleRequest(BaseModel):
    """更新对话标题请求"""
    title: str


class DeleteConversationResponse(BaseModel):
    """删除对话响应"""
    success: bool


class SuccessResponse(BaseModel):
    """通用成功响应"""
    success: bool
