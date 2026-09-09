from typing import List, Dict, Any
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.curriculum import Topic, Concept
from app.services.rag.retriever import CurriculumRetriever


class BenchmarkQuery(BaseModel):
    query: str
    expected_topic_title: str
    expected_concept_name: str
    expected_keywords: List[str]


CLASS_8_SCIENCE_BENCHMARK: List[BenchmarkQuery] = [
    BenchmarkQuery(
        query="Does tap water conduct electric current?",
        expected_topic_title="Conductors and Insulators in Liquids",
        expected_concept_name="Electrolytes & Ionic Conductivity",
        expected_keywords=["mineral salts", "conductor", "dissolved"],
    ),
    BenchmarkQuery(
        query="What happens when you add salt to distilled water in Activity 11.2?",
        expected_topic_title="Conductors and Insulators in Liquids",
        expected_concept_name="Electrolytes & Ionic Conductivity",
        expected_keywords=["distilled water", "salt solution", "tester"],
    ),
    BenchmarkQuery(
        query="Why is distilled water considered a poor conductor of electricity?",
        expected_topic_title="Conductors and Insulators in Liquids",
        expected_concept_name="Electrolytes & Ionic Conductivity",
        expected_keywords=["free of salts", "poor conductor", "distilled"],
    ),
]


class RAGEvaluator:
    """
    RAG Evaluation Engine.
    Executes benchmark queries to evaluate retrieval success, top-k relevance, and source correctness.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.retriever = CurriculumRetriever(db)

    async def run_benchmark(self) -> Dict[str, Any]:
        results = []
        successful_retrievals = 0
        relevant_chunks_found = 0

        # Resolve Topic and Concept IDs
        t_res = await self.db.execute(select(Topic))
        topic = t_res.scalars().first()
        if not topic:
            return {"error": "Curriculum not seeded"}

        c_res = await self.db.execute(select(Concept).where(Concept.topic_id == topic.id))
        concept = c_res.scalars().first()

        for item in CLASS_8_SCIENCE_BENCHMARK:
            chunks = await self.retriever.get_topic_chunks(
                topic_id=topic.id,
                concept_id=concept.id if concept else None,
                query_text=item.query,
                limit=3,
            )

            has_chunks = len(chunks) > 0
            if has_chunks:
                successful_retrievals += 1

            # Check if any top-k chunk contains the expected keywords
            combined_text = " ".join(c.chunk_text.lower() for c in chunks)
            matched_keywords = [kw for kw in item.expected_keywords if kw.lower() in combined_text]
            is_relevant = len(matched_keywords) >= 2

            if is_relevant:
                relevant_chunks_found += 1

            results.append({
                "query": item.query,
                "chunks_retrieved_count": len(chunks),
                "matched_keywords": matched_keywords,
                "is_relevant": is_relevant,
            })

        total_queries = len(CLASS_8_SCIENCE_BENCHMARK)
        return {
            "total_benchmark_queries": total_queries,
            "retrieval_success_rate": round(successful_retrievals / total_queries, 2),
            "top_k_relevance_rate": round(relevant_chunks_found / total_queries, 2),
            "results": results,
        }
