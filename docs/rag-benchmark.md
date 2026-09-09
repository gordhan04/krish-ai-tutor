# RAG Retrieval Benchmark & Accuracy Report

The Curriculum RAG system evaluates retrieval precision, semantic grounding, and citation integrity across NCERT Class 8 Science textbooks.

---

## 1. Benchmark Suite (`CLASS_8_SCIENCE_BENCHMARK`)

The benchmark queries evaluate retrieval across foundational chapters:
- **Chapter 11: Chemical Effects of Electric Current** (Liquid conductivity, dissolved salts, electrodes)
- **Chapter 4: Combustion and Flame** (Chemical oxidation, ignition temperature, flame structure, calorific value)

| Query ID | Target Chapter | Student Question | Expected Topic / Concept | Required Grounding Terms |
| :--- | :--- | :--- | :--- | :--- |
| **Q1** | Ch 11 | *"Does tap water conduct electric current?"* | Conductors and Insulators in Liquids / Electrolytes | `mineral salts`, `conductor`, `dissolved` |
| **Q2** | Ch 11 | *"What happens when you add salt to distilled water in Activity 11.2?"* | Conductors and Insulators in Liquids / Electrolytes | `distilled water`, `salt solution`, `tester` |
| **Q3** | Ch 11 | *"Why is distilled water considered a poor conductor of electricity?"* | Conductors and Insulators in Liquids / Electrolytes | `free of salts`, `poor conductor`, `distilled` |
| **Q4** | Ch 4 | *"What is combustion and what is produced during the chemical reaction?"* | Combustion / What is Combustion | `chemical process`, `oxygen`, `heat` |
| **Q5** | Ch 4 | *"What is ignition temperature and why does a matchstick catch fire on friction?"* | Combustion / Ignition Temperature | `lowest temperature`, `ignition`, `catches fire` |
| **Q6** | Ch 4 | *"How does carbon dioxide extinguish electrical fires?"* | Control Fire / Fire Extinguishing | `carbon dioxide`, `blanket`, `oxygen` |

---

## 2. Evaluation Metrics

Retrieval accuracy is measured along three dimensions:

1. **Retrieval Success Rate (Top-$k$ Availability)**:
   $$\text{Success Rate} = \frac{\sum \mathbb{I}(\text{Retrieved Chunks} \ge 1)}{N}$$
   Target: **100% (1.00)**. Ensures Krish is never left without curriculum context when answering lesson questions.

2. **Top-$k$ Relevance Rate (Semantic Grounding)**:
   $$\text{Relevance Rate} = \frac{\sum \mathbb{I}(\text{Matched Terms} \ge 2)}{N}$$
   Target: **$\ge 80\%$**. Chunks must contain authentic textbook terminology relevant to the prompt.

3. **Citations Verifiability**:
   Every retrieved chunk must carry valid, non-null `page_start`, `page_end`, and `chapter_id`. Hallucinated page numbers are strictly forbidden.

4. **Publication Status Gating**:
   Chunks in `DRAFT` or `REVIEWED` status receive a retrieval score of $0.0$ and are completely filtered before passing to the prompt context.

---

## 3. Automated Benchmark Execution

The benchmark is executed automatically in the CI test suite via:
```bash
pytest backend/tests/test_rag_benchmark.py -v
```

Current Benchmark Performance (Hermetic Test Harness):
- **Retrieval Success Rate:** `100%` (`1.0`)
- **Top-$k$ Relevance Rate:** `100%` (`1.0` on seeded Chapter 11; `1.0` on published Chapter 4)
- **Zero Draft Leaks:** Verified (`test_curriculum_publishing_and_rag.py`)
- **Page Citation Accuracy:** `100%` match with textbook generator fixture
