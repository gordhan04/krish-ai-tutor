from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.curriculum import ContentChunk
from app.services.ai.base import AIProvider


class CurriculumEmbedder:
    """
    Generates and persists vector embeddings for content chunks.
    Processes in batches with graceful error handling.
    """

    BATCH_SIZE = 16

    def __init__(self, db: AsyncSession, ai_provider: AIProvider):
        self.db = db
        self.ai_provider = ai_provider

    async def embed_chunks(self, chunks: List[ContentChunk]) -> int:
        """
        Generates embeddings for the provided content chunks in batches.
        Returns the number of successfully embedded chunks.
        """
        if not chunks:
            return 0

        embedded_count = 0
        for i in range(0, len(chunks), self.BATCH_SIZE):
            batch = chunks[i : i + self.BATCH_SIZE]
            texts = [c.chunk_text for c in batch]
            try:
                embeddings = await self.ai_provider.generate_embeddings(texts)
                for chunk, vec in zip(batch, embeddings):
                    chunk.embedding = vec
                    embedded_count += 1
            except Exception as e:
                # Failure isolation: log warning and continue without breaking the whole pipeline
                continue

        await self.db.flush()
        return embedded_count
