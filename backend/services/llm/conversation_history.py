"""
对话历史管理 - 增删查改，上下文裁剪
"""
from typing import List
from models.schemas import ConversationMessage


class ConversationHistory:
    """对话历史管理器，支持自动裁剪保留最近 N 条消息"""

    def __init__(self, max_messages: int = 50):
        if max_messages < 1:
            raise ValueError(f"max_messages must be at least 1, got {max_messages}")
        self._messages: List[ConversationMessage] = []
        self._max_messages = max_messages

    def add_message(self, message: ConversationMessage) -> None:
        """添加消息，超过最大长度时裁剪保留最近的"""
        self._messages.append(message)
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages:]

    def get_messages(self) -> List[ConversationMessage]:
        """获取所有消息"""
        return self._messages.copy()

    def clear(self) -> None:
        """清空历史"""
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)
