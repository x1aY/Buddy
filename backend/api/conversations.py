"""Conversation history API endpoints."""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import List
from uuid import UUID

from models.conversation import (
    ConversationListResponse,
    ConversationListItem,
    ConversationDetailResponse,
    CreateConversationRequest,
    CreateConversationResponse,
    AddMessageRequest,
    AddMessageResponse,
    UpdateConversationTitleRequest,
    DeleteConversationResponse,
    SuccessResponse,
)
from storage.conversation_storage import (
    list_conversations_for_user,
    get_conversation,
    get_messages_for_conversation,
    create_conversation,
    add_message as storage_add_message,
    delete_conversation_and_messages,
    update_conversation_title,
    set_active_conversation,
)
from vector_store.chroma_client import (
    add_message as chroma_add_message,
    delete_conversation_vectors,
)
from services.embedding import get_embedding_service
from utils.jwt import verify_jwt_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])
security = HTTPBearer(auto_error=False)


def get_user_id_from_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract user ID from JWT token.

    If no token is provided (guest mode), returns the default public guest user ID.

    Raises:
        HTTPException: If token is provided but invalid
    """
    # If no credentials (no Authorization header), use default guest user
    if credentials is None or not credentials.credentials:
        return "guest-public-user"

    token = credentials.credentials
    payload = verify_jwt_token(token)
    if payload is None:
        # Invalid token - still allow guest access instead of rejecting
        return "guest-public-user"
    return payload.userId


@router.get("", response_model=ConversationListResponse)
def list_conversations(user_id: str = Depends(get_user_id_from_token)) -> ConversationListResponse:
    """Get all conversations for the current user.

    Returns:
        List of conversations ordered by updated_at descending
    """
    conversations = list_conversations_for_user(user_id)

    items: List[ConversationListItem] = []
    for conv in conversations:
        items.append(ConversationListItem(
            id=str(conv.id),
            title=conv.title or "New conversation",
            updated_at=conv.updated_at.isoformat(),
            is_active=conv.is_active
        ))

    return ConversationListResponse(conversations=items)


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation_detail(
    conversation_id: UUID,
    user_id: str = Depends(get_user_id_from_token)
) -> ConversationDetailResponse:
    """Get full conversation details including all messages.

    Args:
        conversation_id: Conversation UUID
        user_id: Current authenticated user ID

    Returns:
        Conversation with all messages
    """
    conv = get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Verify ownership
    if conv.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")

    messages = get_messages_for_conversation(conversation_id)

    # Format messages for response
    message_list = [{
        "role": msg.role,
        "content": msg.content,
        "created_at": msg.created_at.isoformat()
    } for msg in messages]

    return ConversationDetailResponse(
        id=str(conv.id),
        title=conv.title or "New conversation",
        messages=message_list
    )


@router.post("", response_model=CreateConversationResponse)
def create_new_conversation(
    request: CreateConversationRequest,
    user_id: str = Depends(get_user_id_from_token)
) -> CreateConversationResponse:
    """Create a new empty conversation.

    Args:
        request: Create conversation request with optional title
        user_id: Current authenticated user ID

    Returns:
        Created conversation ID and title
    """
    title = request.title or ""
    conv = create_conversation(user_id, title, is_active=True)

    # Set this as the active conversation for the user
    set_active_conversation(user_id, conv.id)

    return CreateConversationResponse(
        id=str(conv.id),
        title=conv.title or "New conversation"
    )


@router.post("/{conversation_id}/messages", response_model=AddMessageResponse)
async def add_message_to_conversation(
    conversation_id: UUID,
    request: AddMessageRequest,
    user_id: str = Depends(get_user_id_from_token)
) -> AddMessageResponse:
    """Add a new message to an existing conversation and generate embedding.

    Args:
        conversation_id: Conversation UUID
        request: Add message request with role and content
        user_id: Current authenticated user ID

    Returns:
        Success status and message ID
    """
    conv = get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this conversation")

    # Add message to CSV storage
    msg = storage_add_message(conversation_id, request.role, request.content)

    # Update conversation updated_at and set title if this is the first message and title is empty
    if (not conv.title or conv.title == "") and request.role == "user":
        # Take first 30 characters of first user message as title
        title_preview = request.content[:30] + ("..." if len(request.content) > 30 else "")
        update_conversation_title(conversation_id, title_preview)

    # Try to generate embedding and add to vector store
    embedding_service = get_embedding_service()
    if embedding_service.is_configured():
        embedding = await embedding_service.get_embedding(request.content)
        if embedding is not None:
            chroma_add_message(
                message_id=str(msg.id),
                conversation_id=str(conversation_id),
                role=request.role,
                content=request.content,
                embedding=embedding,
                created_at=msg.created_at.isoformat()
            )

    return AddMessageResponse(
        success=True,
        message_id=str(msg.id)
    )


@router.put("/{conversation_id}", response_model=SuccessResponse)
def update_title(
    conversation_id: UUID,
    request: UpdateConversationTitleRequest,
    user_id: str = Depends(get_user_id_from_token)
) -> SuccessResponse:
    """Update conversation title.

    Args:
        conversation_id: Conversation UUID
        request: Update title request
        user_id: Current authenticated user ID

    Returns:
        Success status
    """
    conv = get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this conversation")

    success = update_conversation_title(conversation_id, request.title)
    return SuccessResponse(success=success)


@router.delete("/{conversation_id}", response_model=DeleteConversationResponse)
def delete_conversation(
    conversation_id: UUID,
    user_id: str = Depends(get_user_id_from_token)
) -> DeleteConversationResponse:
    """Delete a conversation and all its messages (including vector embeddings).

    Args:
        conversation_id: Conversation UUID
        user_id: Current authenticated user ID

    Returns:
        Success status
    """
    conv = get_conversation(conversation_id)
    if conv is None:
        # Conversation already deleted - still return success to frontend
        logger.info("Conversation already deleted, returning success", extra={"conversation_id": str(conversation_id)})
        return DeleteConversationResponse(success=True)

    if conv.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this conversation")

    # Delete from CSV storage
    success = delete_conversation_and_messages(conversation_id)

    if success:
        # Delete from vector store - ignore errors, conversation already deleted from CSV
        try:
            delete_conversation_vectors(str(conversation_id))
        except Exception as e:
            # If vector deletion fails, it's okay - conversation is already gone from main storage
            # Log the error but don't fail the whole request
            logger.warning(
                "Failed to delete conversation vectors from ChromaDB, conversation already deleted from main storage",
                extra={"conversation_id": str(conversation_id), "error": str(e)}
            )

    return DeleteConversationResponse(success=success)


@router.put("/{conversation_id}/active", response_model=SuccessResponse)
def set_conversation_active(
    conversation_id: UUID,
    user_id: str = Depends(get_user_id_from_token)
) -> SuccessResponse:
    """Set a conversation as the active one for the user.

    Args:
        conversation_id: Conversation UUID to set as active
        user_id: Current authenticated user ID

    Returns:
        Success status
    """
    conv = get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to set this conversation as active")

    # Set this as the active conversation
    set_active_conversation(user_id, conversation_id)

    return SuccessResponse(success=True)
