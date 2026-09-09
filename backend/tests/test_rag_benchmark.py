import pytest
from app.services.rag.benchmark import RAGEvaluator


@pytest.mark.asyncio
async def test_rag_benchmark_precision_and_grounding(db_session):
    evaluator = RAGEvaluator(db_session)
    benchmark_report = await evaluator.run_benchmark()

    assert "error" not in benchmark_report
    assert benchmark_report["total_benchmark_queries"] == 3
    assert benchmark_report["retrieval_success_rate"] == 1.0  # 100% of benchmark queries retrieved valid chunks
    assert benchmark_report["top_k_relevance_rate"] >= 0.66   # At least 2/3 queries had high keyword relevance
