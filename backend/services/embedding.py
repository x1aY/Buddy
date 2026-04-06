"""Embedding generation service - supports OpenAI and Anthropic compatible APIs."""

import httpx
from typing import List, Optional
from config import settings


class EmbeddingService:
    """Embedding generation service that works with OpenAI-compatible APIs.

    Most embedding providers (OpenAI, Anthropic, Doubao, etc.) follow the
    OpenAI embedding API format, so we can use a single implementation.
    """

    def __init__(self):
        # Use OpenAI embedding endpoint format regardless of provider
        if settings.openai_api_key and settings.openai_api_key != "":
            self.api_key = settings.openai_api_key
            self.base_url = settings.openai_base_url
        else:
            # Fall back to Anthropic if OpenAI is not configured
            self.api_key = settings.anthropic_auth_token or ""
            self.base_url = settings.anthropic_base_url or "https://api.anthropic.com"

    def is_configured(self) -> bool:
        """Check if embedding service is configured."""
        return self.api_key is not None and self.api_key != ""

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding vector for text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats, None on error
        """
        if not self.is_configured():
            return None

        # Clean text - truncate if too long
        # Most embedding models have context limit around 8192 tokens
        text = text.strip()
        # Truncate to ~4000 tokens (rough estimate 4 chars per token)
        if len(text) > 16000:
            text = text[:16000]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "input": text,
            "model": "text-embedding-3-small"  # OpenAI default, works for most providers
        }

        # OpenAI uses /v1/embeddings endpoint
        url = f"{self.base_url.rstrip('/')}/v1/embeddings"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers=headers, json=data)
                if response.status_code != 200:
                    return None

                result = response.json()
                if "data" in result and len(result["data"]) > 0:
                    return result["data"][0]["embedding"]

                return None
        except Exception:
            return None


# Global singleton instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
