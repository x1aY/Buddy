"""Conversation and message storage using CSV files."""

import csv
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4

from models.conversation import Conversation, Message
from .csv_storage import CSVStorage


# Project root / backend/data/
DATA_DIR = Path(__file__).parent.parent / "data"


# ===== Conversation conversion functions =====

def conversation_to_dict(conv: Conversation) -> dict:
    """Convert Conversation to CSV row dict."""
    return {
        'id': str(conv.id),
        'user_id': conv.user_id,
        'title': conv.title,
        'created_at': conv.created_at.isoformat(),
        'updated_at': conv.updated_at.isoformat(),
        'is_active': str(conv.is_active).lower(),
    }


def dict_to_conversation(row: dict) -> Conversation:
    """Convert CSV row dict to Conversation."""
    return Conversation(
        id=UUID(row.get('id', '')),
        user_id=row.get('user_id', ''),
        title=row.get('title', ''),
        created_at=datetime.fromisoformat(row.get('created_at', datetime.now().isoformat())),
        updated_at=datetime.fromisoformat(row.get('updated_at', datetime.now().isoformat())),
        is_active=row.get('is_active', 'false').lower() == 'true',
    )


# ===== Message conversion functions =====

def message_to_dict(msg: Message) -> dict:
    """Convert Message to CSV row dict."""
    return {
        'id': str(msg.id),
        'conversation_id': str(msg.conversation_id),
        'role': msg.role,
        'content': msg.content,
        'created_at': msg.created_at.isoformat(),
    }


def dict_to_message(row: dict) -> Message:
    """Convert CSV row dict to Message."""
    return Message(
        id=UUID(row.get('id', '')),
        conversation_id=UUID(row.get('conversation_id', '')),
        role=row.get('role', ''),
        content=row.get('content', ''),
        created_at=datetime.fromisoformat(row.get('created_at', datetime.now().isoformat())),
    )


# ===== Lazy initialized storage instances =====

_conversation_storage: CSVStorage[Conversation] | None = None
_message_storage: CSVStorage[Message] | None = None


def _get_conversation_storage() -> CSVStorage[Conversation]:
    """Get or create the conversation storage instance (lazy initialization)."""
    global _conversation_storage
    if _conversation_storage is None:
        _conversation_storage = CSVStorage[Conversation](
            file_path=DATA_DIR / "conversations.csv",
            headers=[
                'id',
                'user_id',
                'title',
                'created_at',
                'updated_at',
                'is_active',
            ],
            row_to_dict=conversation_to_dict,
            dict_to_row=dict_to_conversation
        )
    return _conversation_storage


def _get_message_storage() -> CSVStorage[Message]:
    """Get or create the message storage instance (lazy initialization)."""
    global _message_storage
    if _message_storage is None:
        _message_storage = CSVStorage[Message](
            file_path=DATA_DIR / "messages.csv",
            headers=[
                'id',
                'conversation_id',
                'role',
                'content',
                'created_at',
            ],
            row_to_dict=message_to_dict,
            dict_to_row=dict_to_message
        )
    return _message_storage


# ===== Public API =====

def list_conversations_for_user(user_id: str) -> List[Conversation]:
    """Get all conversations for a user, ordered by updated_at descending.

    Args:
        user_id: User identifier

    Returns:
        List of conversations, newest first
    """
    storage = _get_conversation_storage()
    convs = storage.filter(lambda conv: conv.user_id == user_id)
    # Sort by updated_at descending
    convs.sort(key=lambda c: c.updated_at, reverse=True)
    return convs


def get_conversation(conversation_id: UUID) -> Optional[Conversation]:
    """Get a conversation by ID.

    Args:
        conversation_id: Conversation UUID

    Returns:
        Conversation if found, None otherwise
    """
    storage = _get_conversation_storage()
    convs = storage.filter(lambda conv: conv.id == conversation_id)
    return convs[0] if convs else None


def get_messages_for_conversation(conversation_id: UUID) -> List[Message]:
    """Get all messages for a conversation, ordered by created_at ascending.

    Args:
        conversation_id: Conversation UUID

    Returns:
        List of messages, oldest first
    """
    storage = _get_message_storage()
    msgs = storage.filter(lambda msg: msg.conversation_id == conversation_id)
    # Sort by created_at ascending
    msgs.sort(key=lambda m: m.created_at)
    return msgs


def create_conversation(
    user_id: str,
    title: str = "",
    is_active: bool = False
) -> Conversation:
    """Create a new conversation.

    Args:
        user_id: User identifier
        title: Conversation title (usually from first message)
        is_active: Whether this is the active conversation

    Returns:
        The created conversation
    """
    conv = Conversation(
        id=uuid4(),
        user_id=user_id,
        title=title,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        is_active=is_active,
    )
    storage = _get_conversation_storage()
    storage.append(conv)
    return conv


def add_message(
    conversation_id: UUID,
    role: str,
    content: str
) -> Message:
    """Add a new message to a conversation.
    Also updates the conversation's updated_at timestamp.

    Args:
        conversation_id: Conversation UUID
        role: Message role ('user' or 'model')
        content: Message content

    Returns:
        The created message
    """
    msg = Message(
        id=uuid4(),
        conversation_id=conversation_id,
        role=role,
        content=content,
        created_at=datetime.now(),
    )
    storage = _get_message_storage()
    storage.append(msg)
    return msg


def delete_conversation_and_messages(conversation_id: UUID) -> bool:
    """Delete a conversation and all its messages.

    Args:
        conversation_id: Conversation UUID to delete

    Returns:
        True if deleted successfully, False if not found
    """
    # First check if conversation exists
    conv = get_conversation(conversation_id)
    if conv is None:
        return False

    # Rewrite conversation storage without this conversation
    conv_storage = _get_conversation_storage()
    all_convs = conv_storage.load_all()
    all_convs = [c for c in all_convs if c.id != conversation_id]

    # Rewrite file
    with open(conv_storage.file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=conv_storage.headers)
        writer.writeheader()
        for c in all_convs:
            writer.writerow(conversation_to_dict(c))

    # Delete all messages for this conversation
    msg_storage = _get_message_storage()
    all_msgs = msg_storage.load_all()
    all_msgs = [m for m in all_msgs if m.conversation_id != conversation_id]

    # Rewrite file
    with open(msg_storage.file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=msg_storage.headers)
        writer.writeheader()
        for m in all_msgs:
            writer.writerow(message_to_dict(m))

    return True


def update_conversation_title(conversation_id: UUID, title: str) -> bool:
    """Update conversation title.

    Args:
        conversation_id: Conversation UUID
        title: New title

    Returns:
        True if updated successfully
    """
    conv_storage = _get_conversation_storage()
    all_convs = conv_storage.load_all()
    updated = False

    for conv in all_convs:
        if conv.id == conversation_id:
            conv.title = title
            conv.updated_at = datetime.now()
            updated = True
            break

    if not updated:
        return False

    # Rewrite file
    with open(conv_storage.file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=conv_storage.headers)
        writer.writeheader()
        for c in all_convs:
            writer.writerow(conversation_to_dict(c))

    return True


def set_active_conversation(user_id: str, conversation_id: UUID) -> None:
    """Set the active conversation for a user (only one active at a time).

    Args:
        user_id: User identifier
        conversation_id: Conversation to set as active
    """
    conv_storage = _get_conversation_storage()
    all_convs = conv_storage.load_all()

    # Update all conversations for this user
    for conv in all_convs:
        if conv.user_id == user_id:
            conv.is_active = (conv.id == conversation_id)

    # Rewrite file
    with open(conv_storage.file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=conv_storage.headers)
        writer.writeheader()
        for c in all_convs:
            writer.writerow(conversation_to_dict(c))


def count_conversations_for_user(user_id: str) -> int:
    """Count conversations for a user.

    Args:
        user_id: User identifier

    Returns:
        Number of conversations
    """
    return len(list_conversations_for_user(user_id))
