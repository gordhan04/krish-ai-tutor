import math
import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.curriculum import ContentChunk, Chapter, Topic, Concept, Book, CurriculumDocument

logger = logging.getLogger("krish_ai_tutor.retriever")

STOPWORDS = {
    # Grammar stopwords
    "what", "which", "who", "whom", "whose", "why", "where", "when", "how",
    "does", "doing", "done", "will", "would", "shall", "should", "can", "could",
    "may", "might", "must", "have", "has", "had", "having", "been", "being",
    "were", "with", "without", "into", "onto", "upon", "from", "about", "above",
    "below", "between", "both", "each", "other", "some", "such", "than", "that",
    "their", "them", "then", "there", "these", "they", "this", "those", "through",
    "under", "until", "very", "your", "yours", "the", "and", "for", "are", "not",
    "any", "all", "but", "also", "explain", "describe", "discuss", "give", "name",
    "show", "tell", "difference", "differences", "comparison", "compare", "define",
    "definition", "meaning", "used", "like", "many", "much", "more", "most",
    "its", "it", "itself", "causes", "caused", "causing",
    "up", "down", "over", "off", "out",
    # Instructional / generic non-domain words
    "book", "chapter", "contents", "concepts", "activity", "activities", "figure",
    "figures", "table", "different", "types", "various", "things", "items",
}


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
    """Calculates keyword overlap score between substantive query terms and chunk text."""
    if not query or not text:
        return 0.0
    raw_words = [w.lower() for w in re.split(r'\W+', query) if len(w) > 2]
    content_query_words = [w for w in raw_words if w not in STOPWORDS]
    if not content_query_words:
        # Check if query was asking for a specific chapter number
        m = re.search(r'\bchapter\s*(\d+)\b', query.lower())
        if m:
            return 0.0
        content_query_words = raw_words
    if not content_query_words:
        return 0.0
    unique_content = set(content_query_words)
    text_words = set(w.lower() for w in re.split(r'\W+', text) if len(w) > 2)
    overlap = unique_content.intersection(text_words)
    if not overlap:
        return 0.0

    # Specificity check:
    # If query has >= 3 content words, require at least 2 matching content words
    # and at least 55% overlap, preventing incidental words (e.g. 'plant' or 'cell' in 'pencil cell')
    # from triggering false positive grounding on out-of-scope queries.
    ratio = len(overlap) / len(unique_content)
    if len(unique_content) >= 3:
        if ratio < 0.55 or len(overlap) < 2:
            return 0.0
    elif len(unique_content) == 2:
        if ratio < 0.50:
            return 0.0

    return ratio


@dataclass
class CurriculumScope:
    """
    Deterministic curriculum isolation boundary.
    Queries outside this scope are strictly rejected.
    """
    document_id: Optional[str] = None
    book_id: Optional[str] = None
    subject_id: Optional[str] = None
    chapter_id: Optional[str] = None
    section_id: Optional[str] = None
    topic_id: Optional[str] = None
    concept_id: Optional[str] = None
    allow_document_fallback: bool = False


class RetrievalResult(BaseModel):
    """Structured retrieval response enforcing grounded source availability."""
    grounded: bool
    source_available: bool
    reason: Optional[str] = None
    chunks: List[Any] = []
    formatted_context: str = ""
    citations: List[str] = []
    provenance_errors: List[str] = []
    debug_metadata: Optional[Dict[str, Any]] = None


class CurriculumRetriever:
    """
    Curriculum-aware retriever with strict hierarchical metadata filtering,
    hard provenance invariant enforcement, and prompt injection defense.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def scoped_retrieval(
        self,
        query_text: str,
        scope: CurriculumScope,
        limit: int = 4,
        status_filter: str = "PUBLISHED",
        include_front_matter: bool = False,
    ) -> RetrievalResult:
        """
        Executes strict curriculum-isolated retrieval:
        1. Validates document authorization and metadata
        2. Applies SQL filters (document_id, chapter_id, section_id)
        3. Computes lexical & vector relevance
        4. Validates Hard Provenance Invariant (page <= max_physical, doc_id matches)
        5. Returns structured RetrievalResult (grounded=False if out-of-scope)
        """
        debug_info: Dict[str, Any] = {
            "query": query_text,
            "scope": {
                "document_id": scope.document_id,
                "chapter_id": scope.chapter_id,
                "section_id": scope.section_id,
            },
            "candidate_count": 0,
            "filtered_count": 0,
        }

        # Step 1: Validate Document Scope if provided
        doc: Optional[CurriculumDocument] = None
        if scope.document_id:
            doc = await self.db.get(CurriculumDocument, scope.document_id)
            if not doc:
                return RetrievalResult(
                    grounded=False,
                    source_available=False,
                    reason="DOCUMENT_NOT_FOUND",
                    debug_metadata=debug_info,
                )
            if doc.status not in (status_filter, "PUBLISHED", "REVIEWED"):
                return RetrievalResult(
                    grounded=False,
                    source_available=False,
                    reason="DOCUMENT_NOT_PUBLISHED",
                    debug_metadata=debug_info,
                )

        # Step 2: Build Base Query
        stmt = (
            select(ContentChunk)
            .where(ContentChunk.status == status_filter)
            .options(
                selectinload(ContentChunk.concept),
                selectinload(ContentChunk.chapter),
                selectinload(ContentChunk.section),
                selectinload(ContentChunk.document),
            )
        )

        if scope.document_id:
            stmt = stmt.where(ContentChunk.document_id == scope.document_id)
        if scope.book_id:
            stmt = stmt.where(ContentChunk.book_id == scope.book_id)

        # Front matter exclusion
        is_front_matter_query = any(
            w in query_text.lower()
            for w in ["contents", "table of contents", "index", "preface", "foreword", "chapters in this book"]
        )
        if not include_front_matter and not is_front_matter_query:
            stmt = stmt.where(ContentChunk.content_type != "FRONT_MATTER")

        # Step 3: Hierarchical Scoping (Section -> Chapter -> Document)
        active_stmt = stmt
        if scope.section_id:
            active_stmt = active_stmt.where(ContentChunk.section_id == scope.section_id)
        elif scope.chapter_id:
            active_stmt = active_stmt.where(ContentChunk.chapter_id == scope.chapter_id)

        res = await self.db.execute(active_stmt)
        candidates = list(res.scalars().all())

        # If section filter yielded nothing and fallback allowed, try chapter
        if not candidates and scope.section_id and scope.allow_document_fallback:
            if scope.chapter_id:
                fallback_stmt = stmt.where(ContentChunk.chapter_id == scope.chapter_id)
                fb_res = await self.db.execute(fallback_stmt)
                candidates = list(fb_res.scalars().all())

        # If chapter filter yielded nothing and fallback allowed, try document
        if not candidates and scope.chapter_id and scope.allow_document_fallback:
            fb_res = await self.db.execute(stmt)
            candidates = list(fb_res.scalars().all())

        debug_info["candidate_count"] = len(candidates)
        if not candidates:
            return RetrievalResult(
                grounded=False,
                source_available=False,
                reason="NO_CHUNKS_IN_REQUESTED_SCOPE",
                debug_metadata=debug_info,
            )

        # Step 4: Relevance Scoring
        q_lower = query_text.lower()
        scored: List[tuple[float, ContentChunk]] = []

        m_act = re.search(r'\bactivity\s*(\d+\.\d+)\b', q_lower)
        m_fig = re.search(r'\b(?:fig|figure)\.?\s*(\d+\.\d+)\b', q_lower)

        for chunk in candidates:
            score = calculate_lexical_score(query_text, chunk.chunk_text)
            c_type = str(chunk.content_type).upper()

            # Exact curriculum entity match (Activity 9.1 or Fig. 4.1)
            if m_act:
                act_num = m_act.group(1)
                if act_num in chunk.chunk_text and ("activity" in chunk.chunk_text.lower() or "ACTIVITY" in c_type):
                    score += 0.8
            elif m_fig:
                fig_num = m_fig.group(1)
                if fig_num in chunk.chunk_text and ("fig" in chunk.chunk_text.lower() or "FIGURE" in c_type):
                    score += 0.8

            # Boost if substantive content keywords matched!
            if score > 0.0:
                if "activity" in q_lower and ("ACTIVITY" in c_type or "EXPERIMENT" in c_type):
                    score += 0.3
                if "fig" in q_lower or "figure" in q_lower:
                    if "FIGURE" in c_type:
                        score += 0.3
                if any(w in q_lower for w in ["what is", "define", "definition", "meaning"]) and "DEFINITION" in c_type:
                    score += 0.25

            if score >= 0.10:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [c for _, c in scored[:limit]]

        if not top_candidates:
            return RetrievalResult(
                grounded=False,
                source_available=False,
                reason="NO_RELEVANT_SOURCE_IN_SELECTED_CURRICULUM",
                debug_metadata=debug_info,
            )

        # Step 5: Hard Provenance Invariant Check
        valid_chunks: List[ContentChunk] = []
        provenance_errors: List[str] = []

        for chunk in top_candidates:
            # 1. Document boundary
            if doc:
                if chunk.document_id and chunk.document_id != doc.id:
                    err = f"Cross-document contamination: chunk {chunk.id} has doc {chunk.document_id} != scope doc {doc.id}"
                    logger.error(err)
                    provenance_errors.append(err)
                    continue

                # 2. PDF page bounds
                pdf_p = getattr(chunk, "pdf_page_number", None) or chunk.page_number
                if doc.page_count and doc.page_count > 0:
                    if pdf_p < 1 or pdf_p > doc.page_count:
                        err = f"Impossible PDF page {pdf_p} for chunk {chunk.id} in doc {doc.id} (max {doc.page_count})"
                        logger.error(err)
                        provenance_errors.append(err)
                        continue

                # 3. Printed page bounds
                pr_p = getattr(chunk, "printed_page_number", None)
                if pr_p is not None and doc.printed_page_end:
                    min_pr = doc.printed_page_start or 1
                    if pr_p < min_pr or pr_p > doc.printed_page_end:
                        err = f"Impossible printed page {pr_p} for chunk {chunk.id} (range {min_pr}–{doc.printed_page_end})"
                        logger.error(err)
                        provenance_errors.append(err)
                        continue

            valid_chunks.append(chunk)

        debug_info["filtered_count"] = len(valid_chunks)

        if not valid_chunks:
            return RetrievalResult(
                grounded=False,
                source_available=False,
                reason="PROVENANCE_INVARIANT_VIOLATION",
                provenance_errors=provenance_errors,
                debug_metadata=debug_info,
            )

        # Step 6: Format Context & Citations
        citations = []
        for c in valid_chunks:
            ch_name = c.chapter.title if c.chapter else "Class 8 Science"
            pr_p = getattr(c, "printed_page_number", None)
            pdf_p = getattr(c, "pdf_page_number", None) or c.page_number
            if pr_p:
                citations.append(f"Chapter: {ch_name} • Printed Page {pr_p} (PDF Page {pdf_p})")
            else:
                citations.append(f"Chapter: {ch_name} • PDF Page {pdf_p}")

        formatted_context = self.format_context_for_prompt(valid_chunks)

        return RetrievalResult(
            grounded=True,
            source_available=True,
            reason="GROUNDED_SOURCE_RETRIEVED",
            chunks=valid_chunks,
            formatted_context=formatted_context,
            citations=citations,
            provenance_errors=provenance_errors,
            debug_metadata=debug_info,
        )

    async def get_topic_chunks(
        self,
        topic_id: str,
        concept_id: Optional[str] = None,
        query_text: Optional[str] = None,
        limit: int = 4,
    ) -> List[ContentChunk]:
        """
        Retrieves curriculum chunks filtered strictly by topic_id and concept_id.
        """
        stmt = (
            select(ContentChunk)
            .where(ContentChunk.topic_id == topic_id, ContentChunk.status == "PUBLISHED")
            .options(selectinload(ContentChunk.concept), selectinload(ContentChunk.chapter))
        )
        if concept_id:
            stmt = stmt.where(ContentChunk.concept_id == concept_id)

        result = await self.db.execute(stmt)
        chunks = list(result.scalars().all())

        if not chunks and concept_id:
            fallback_stmt = (
                select(ContentChunk)
                .where(ContentChunk.topic_id == topic_id, ContentChunk.status == "PUBLISHED")
                .options(selectinload(ContentChunk.concept), selectinload(ContentChunk.chapter))
            )
            fb_result = await self.db.execute(fallback_stmt)
            chunks = list(fb_result.scalars().all())

        if query_text and chunks:
            scored_chunks = []
            for chunk in chunks:
                score = calculate_lexical_score(query_text, chunk.chunk_text)
                if score > 0:
                    if "activity" in query_text.lower() and chunk.content_type == "experiment":
                        score += 0.2
                    if "why" in query_text.lower() and chunk.content_type == "explanation":
                        score += 0.1
                    scored_chunks.append((score, chunk))

            scored_chunks.sort(key=lambda x: x[0], reverse=True)
            return [chunk for _, chunk in scored_chunks[:limit]]

        return chunks[:limit]

    async def search_textbook_chunks(
        self,
        query_text: str,
        limit: int = 5,
        include_front_matter: bool = False,
        status_filter: str = "PUBLISHED",
        document_id: Optional[str] = None,
        chapter_id: Optional[str] = None,
    ) -> List[ContentChunk]:
        """
        Textbook search scoped by document_id and chapter_id if provided.
        Maintains backward compatibility while enforcing provenance boundaries.
        """
        scope = CurriculumScope(
            document_id=document_id,
            chapter_id=chapter_id,
            allow_document_fallback=(chapter_id is None),
        )
        result = await self.scoped_retrieval(
            query_text=query_text,
            scope=scope,
            limit=limit,
            status_filter=status_filter,
            include_front_matter=include_front_matter,
        )
        return result.chunks

    def format_context_for_prompt(self, chunks: List[ContentChunk]) -> str:
        """
        Formats retrieved chunks with citations and protective boundaries.
        Enforces strict prompt injection defense: content is reference data, not instructions.
        """
        if not chunks:
            return "No specific textbook excerpts available for this topic in the selected curriculum scope."

        formatted_parts = []
        for i, chunk in enumerate(chunks, 1):
            ch_title = chunk.chapter.title if chunk.chapter else "Class 8 Science"
            c_name = chunk.concept.name if chunk.concept else "General Topic"
            pr_p = getattr(chunk, "printed_page_number", None)
            pdf_p = getattr(chunk, "pdf_page_number", None) or chunk.page_number
            page_cite = f"Printed Page {pr_p} (PDF Page {pdf_p})" if pr_p else f"PDF Page {pdf_p}"

            source_tag = (
                f"[Source Excerpt {i} | Chapter: {ch_title} | Concept: {c_name} | "
                f"{page_cite} | Type: {chunk.content_type}]"
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
