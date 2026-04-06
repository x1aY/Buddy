"""ChromaDB vector storage client for conversation messages."""

from pathlib import Path
from typing import List, Optional, Dict
import chromadb

# Data directory for ChromaDB persistence
DATA_DIR = Path(__file__).parent.parent / "data" / "chroma"
COLLECTION_NAME = "conversation_messages"

# Lazy initialized client and collection
_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection] = None


def get_client() -> chromadb.PersistentClient:
    """Get or create the ChromaDB client (lazy initialization)."""
    global _client
    if _client is None:
        # Create data directory if it doesn't exist
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize persistent client (new chromadb API)
        _client = chromadb.PersistentClient(path=str(DATA_DIR))
    return _client


def get_collection() -> chromadb.Collection:
    """Get or create the conversation messages collection."""
    global _collection
    if _collection is None:
        client = get_client()
        # Get or create collection
        collections = client.list_collections()
        if COLLECTION_NAME in collections:
            _collection = client.get_collection(COLLECTION_NAME)
        else:
            _collection = client.create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
    return _collection


def add_message(
    message_id: str,
    conversation_id: str,
    role: str,
    content: str,
    embedding: List[float],
    created_at: str
) -> None:
    """Add a message with its embedding to the vector store.

    Args:
        message_id: Unique message ID
        conversation_id: Conversation ID this message belongs to
        role: Message role ('user' or 'model')
        content: Message content text
        embedding: Embedding vector from LLM
        created_at: Creation timestamp (ISO format)
    """
    collection = get_collection()

    metadata = {
        "conversation_id": conversation_id,
        "role": role,
        "created_at": created_at
    }

    collection.add(
        ids=[message_id],
        embeddings=[embedding],
        documents=[content],
        metadatas=[metadata]
    )


def delete_message(message_id: str) -> None:
    """Delete a message from the vector store.

    Args:
        message_id: Message ID to delete
    """
    collection = get_collection()
    collection.delete(ids=[message_id])


def delete_conversation_vectors(conversation_id: str) -> None:
    """Delete all messages from a conversation.

    Args:
        conversation_id: Conversation ID to delete all vectors for
    """
    collection = get_collection()
    # Delete by where clause metadata
    collection.delete(where={"conversation_id": conversation_id})


def search_similar(
    query_embedding: List[float],
    limit: int = 5,
    where: Optional[Dict] = None
) -> dict:
    """Search for similar messages by query embedding.

    Args:
        query_embedding: Query embedding vector
        limit: Maximum number of results to return
        where: Optional filter metadata (e.g., {"conversation_id": "..."})

    Returns:
        Search results with ids, documents, distances, metadatas
    """
    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=limit,
        where=where
    )
    return results


def count_messages() -> int:
    """Get total number of messages in the collection.

    Returns:
        Number of messages
    """
    collection = get_collection()
    return collection.count()
