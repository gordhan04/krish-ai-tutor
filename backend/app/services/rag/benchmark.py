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
    # Chapter 11: Chemical Effects of Electric Current
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
    # Chapter 4: Combustion and Flame
    BenchmarkQuery(
        query="What is combustion and what is produced during the chemical reaction?",
        expected_topic_title="Combustion",
        expected_concept_name="Combustion",
        expected_keywords=["chemical process", "oxygen", "heat"],
    ),
    BenchmarkQuery(
        query="What is ignition temperature and why does a matchstick catch fire on friction?",
        expected_topic_title="Combustion",
        expected_concept_name="Ignition Temperature",
        expected_keywords=["lowest temperature", "ignition", "catches fire"],
    ),
    BenchmarkQuery(
        query="How does carbon dioxide extinguish electrical fires?",
        expected_topic_title="Control Fire",
        expected_concept_name="Fire",
        expected_keywords=["carbon dioxide", "blanket", "oxygen"],
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

    async def run_benchmark(self, filter_available_topics: bool = True) -> Dict[str, Any]:
        results = []
        successful_retrievals = 0
        relevant_chunks_found = 0
        evaluated_queries = 0

        for item in CLASS_8_SCIENCE_BENCHMARK:
            # Dynamically resolve topic
            stmt = select(Topic).where(Topic.title.ilike(f"%{item.expected_topic_title}%"))
            t_res = await self.db.execute(stmt)
            topic = t_res.scalars().first()

            if not topic:
                if filter_available_topics:
                    continue  # Topic from chapter not seeded in this instance
                results.append({
                    "query": item.query,
                    "status": "topic_not_seeded",
                    "chunks_retrieved_count": 0,
                    "matched_keywords": [],
                    "is_relevant": False,
                })
                evaluated_queries += 1
                continue

            evaluated_queries += 1

            c_res = await self.db.execute(
                select(Concept).where(
                    Concept.topic_id == topic.id,
                    Concept.name.ilike(f"%{item.expected_concept_name}%")
                )
            )
            concept = c_res.scalars().first()

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
                "topic": topic.title,
                "concept": concept.name if concept else None,
                "chunks_retrieved_count": len(chunks),
                "matched_keywords": matched_keywords,
                "is_relevant": is_relevant,
            })

        if evaluated_queries == 0:
            return {"error": "Curriculum not seeded"}

        return {
            "total_benchmark_queries": evaluated_queries,
            "retrieval_success_rate": round(successful_retrievals / evaluated_queries, 2),
            "top_k_relevance_rate": round(relevant_chunks_found / evaluated_queries, 2),
            "results": results,
        }
