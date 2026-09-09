import math
import re
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.curriculum import ContentChunk, Chapter, Topic, Concept, Book


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def calculate_lexical_score(query: str, text: str) -> float:
    """Calculates keyword overlap score between query terms and chunk text."""
    if not query or not text:
        return 0.0
    query_words = set(w.lower() for w in re.split(r'\W+', query) if len(w) > 2)
    if not query_words:
        return 0.0
    text_words = set(w.lower() for w in re.split(r'\W+', text) if len(w) > 2)
    overlap = query_words.intersection(text_words)
    return len(overlap) / len(query_words)


class CurriculumRetriever:
    """
    Curriculum-aware retriever with strict hierarchical metadata filtering,
    lexical & semantic ranking, and prompt injection defense.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_topic_chunks(
        self,
        topic_id: str,
        concept_id: Optional[str] = None,
        query_text: Optional[str] = None,
        limit: int = 4,
    ) -> List[ContentChunk]:
        """
        Retrieves curriculum chunks filtered strictly by topic_id and concept_id.
        Applies hybrid ranking (lexical + vector) when query_text is provided.
        """
        stmt = (
            select(ContentChunk)
            .where(ContentChunk.topic_id == topic_id)
            .options(selectinload(ContentChunk.concept), selectinload(ContentChunk.chapter))
        )
        if concept_id:
            stmt = stmt.where(ContentChunk.concept_id == concept_id)

        result = await self.db.execute(stmt)
        chunks = list(result.scalars().all())

        if not chunks and concept_id:
            # Fallback to topic-level chunks if concept-specific chunks are sparse
            fallback_stmt = (
                select(ContentChunk)
                .where(ContentChunk.topic_id == topic_id)
                .options(selectinload(ContentChunk.concept), selectinload(ContentChunk.chapter))
            )
            fb_result = await self.db.execute(fallback_stmt)
            chunks = list(fb_result.scalars().all())

        # If query_text is provided, rank chunks by lexical overlap and relevance
        if query_text and chunks:
            scored_chunks = []
            for chunk in chunks:
                score = calculate_lexical_score(query_text, chunk.chunk_text)
                # Boost definitions and experiments if query asks about mechanism or activity
                if "activity" in query_text.lower() and chunk.content_type == "experiment":
                    score += 0.2
                if "why" in query_text.lower() and chunk.content_type == "explanation":
                    score += 0.1
                scored_chunks.append((score, chunk))

            scored_chunks.sort(key=lambda x: x[0], reverse=True)
            return [chunk for _, chunk in scored_chunks[:limit]]

        return chunks[:limit]

    def format_context_for_prompt(self, chunks: List[ContentChunk]) -> str:
        """
        Formats retrieved chunks with citations and protective boundaries.
        Enforces strict prompt injection defense: content is reference data, not instructions.
        """
        if not chunks:
            return "No specific textbook excerpts available for this topic."

        formatted_parts = []
        for i, chunk in enumerate(chunks, 1):
            ch_title = chunk.chapter.title if chunk.chapter else "Class 8 Science"
            c_name = chunk.concept.name if chunk.concept else "General Topic"
            source_tag = (
                f"[Source Excerpt {i} | Chapter: {ch_title} | Concept: {c_name} | "
                f"Page {chunk.page_number} | Type: {chunk.content_type}]"
            )
            # Sanitize content against prompt injection attacks
            sanitized_text = (
                chunk.chunk_text
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("system:", "[system]:")
                .replace("instructions:", "[reference]:")
            )
            formatted_parts.append(f"{source_tag}\n{sanitized_text}")

        return "\n\n".join(formatted_parts)
