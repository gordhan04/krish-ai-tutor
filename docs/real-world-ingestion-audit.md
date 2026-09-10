# KRISH AI TUTOR — Real-World PDF Ingestion Audit & Architecture Plan

**Date:** September 10, 2026  
**Subject:** Deep Inspection of `curiosity.pdf` & Root Cause Analysis of Ingestion Failure  
**Status:** Audit Completed $\to$ Implementation Plan Established  

---

## 1. Executive Summary

When the real-world textbook file `curiosity.pdf` (20 pages) was uploaded to the KRISH AI TUTOR Phase B ingestion pipeline, the system produced an unacceptable result:
- **Pages Detected:** 20
- **Chapters Created:** 1 (`"Class 8 Textbook"`)
- **Sections Created:** 1 (`"1.1 Class 8 Textbook"`)
- **Chunks Created:** 1 (containing all ~38,000 characters from all 20 pages in a single chunk!)
- **Questions Generated:** 2 (1 generic MCQ + 1 generic Rubric question)
- **Warning Emitted:** `"No explicit 'Chapter X' header detected; created default chapter container."`

This audit demonstrates that the current parser suffers from:
1. **Fragile regex dependency on explicit `"Chapter X"` patterns** that triggers an immediate fallback on Page 1.
2. **Zero Table of Contents (TOC) awareness**, failing to recognize that Page 19 contains the complete 13-chapter syllabus of NCERT Grade 8 Science.
3. **No header/footer suppression**, polluting curriculum text with InDesign running marks (`0_Prelims.indd 190_Prelims.indd 19...`, `Reprint 2026-27`).
4. **Catastrophic line-aggregation chunking flaw**: all unclassified lines are concatenated into a single string, which `SemanticChunker` treats as a single line and flushes into a single chunk.
5. **Under-scaled question generation**: `CurriculumQuestionGenerator` creates exactly 2 questions per concept, resulting in 2 questions for a 20-page document.

---

## 2. Actual PDF Structure of `curiosity.pdf`

A physical, page-by-page extraction of `curiosity.pdf` reveals that it is the **official 20-page Prelims (Front Matter)** of the NCERT Class 8 Science textbook *"Curiosity"* (2025–26 Reprint Edition):

| Page Number | Page Title / Content | Character Count | Structural Role | Key Identifying Text |
|---|---|---|---|---|
| **Page 1** | Cover / Title Page | 149 chars | Front Matter | `"Curiosity: Textbook of Science for Grade 8"` |
| **Page 2** | Publication Details & Copyright | 2,096 chars | Legal / Metadata | `"First Edition June 2025 Ashadha 1947"`, `"PD 730T SM"` |
| **Page 3** | Foreword (Part 1) | 2,726 chars | Editorial | `"The National Education Policy (NEP) 2020..."`, Page roman `"iii"` |
| **Page 4** | Foreword (Part 2) | 1,558 chars | Editorial | `"understand scientific concepts through real-world contexts"`, Page `"iv"` |
| **Page 5** | About this Book (Part 1) | 2,727 chars | Pedagogical Intro | `"After exploring the Curiosity, Grade 7 textbook..."`, Page `"v"` |
| **Page 6** | About this Book (Part 2) | 2,369 chars | Pedagogical Intro | `"To sustain the students' interest..."`, Page `"vi"` |
| **Page 7** | About this Book (Part 3) | 3,044 chars | Pedagogical Intro | `"applications, showing how science has contributed..."`, Page `"vii"` |
| **Page 8** | About this Book (Part 4) | 1,453 chars | Pedagogical Intro | `"Discover, design, and debate..."`, Page `"viii"` |
| **Page 9** | Committee (NSTC) | 1,662 chars | Academic Team | `"National Syllabus and Teaching Learning Material Committee"` |
| **Page 10** | Blank / Spacer Page | 100 chars | Running Marks | Only running footers (`0_Prelims.indd 10...`, `Reprint 2026-27`) |
| **Page 11** | Contributors (Part 1) | 2,044 chars | Academic Team | `"Contributors: Arnab Bhattacharya... Textbook Development Team"` |
| **Page 12** | Contributors (Part 2) | 2,039 chars | Academic Team | `"Gauri Roy, PGT (Physics)..."`, Page `"xii"` |
| **Page 13** | Contributors (Part 3) | 2,150 chars | Academic Team | `"P.V. Raghavendra... Member-Coordinator"`, Page `"xiii"` |
| **Page 14** | Reviewers (Part 1) | 2,167 chars | Academic Team | `"Reviewers: Shekhar C. Mande, Former Director General CSIR"`, Page `"xiv"` |
| **Page 15** | Reviewers (Part 2) | 951 chars | Academic Team | `"Santosh Gharpure... Satyajit Rath"`, Page `"xv"` |
| **Page 16** | Acknowledgements (Part 1) | 2,621 chars | Front Matter | `"National Council of Educational Research and Training acknowledges..."` |
| **Page 17** | Acknowledgements (Part 2) | 1,196 chars | Front Matter | `"The Council acknowledges the dedicated efforts..."`, Page `"xvii"` |
| **Page 18** | Constitution of India: Duties | 1,742 chars | Constitutional | `"Part IV A (Article 51 A): Fundamental Duties"` |
| **Page 19** | **Table of Contents (TOC)** | 806 chars | **Curriculum TOC** | Lists **Chapters 1 through 13** with titles and starting pages! |
| **Page 20** | Constitution of India: Rights | 1,663 chars | Constitutional | `"Part III (Articles 12 – 35): Fundamental Rights"` |

### Running Footers & Header Patterns Across All Pages:
- **InDesign Artifacts:** `0_Prelims.indd   [page]0_Prelims.indd   [page]  6/30/2025   1:56:17 PM` occurs at the bottom of almost every page.
- **Reprint Notice:** `Reprint 2026-27` occurs at the bottom of almost every page.
- **Section Running Headers:** `Textbook Development Team`, `Acknowledgements`, `Contents`, `Constitution of India`.

---

## 3. Root Cause Analysis: Why the Parser Failed

### 3.1. Premature Fallback Chapter Creation on Page 1
In `backend/app/services/curriculum_ingestion/parser.py`:
```python
for p in pages:
    # Check if this page introduces a new chapter
    chapter_matched = False
    for pattern in cls.CHAPTER_PATTERNS:
        match = re.search(pattern, page_text, re.IGNORECASE)
        ...
    # If no chapter detected yet, initialize a fallback chapter
    if not current_chapter:
        current_chapter = ParsedChapter(chapter_number=1, title=fallback_title, start_page=page_num)
        chapters.append(current_chapter)
        warnings.append("No explicit 'Chapter X' header detected; created default chapter container.")
```
**Defect:**
On Page 1 (Title Cover), `CHAPTER_PATTERNS` does not match. The parser **immediately** creates `current_chapter = ParsedChapter(1, "Class 8 Textbook", 1)`.
Because `current_chapter` is now non-null, every subsequent page checks:
`if not current_chapter or current_chapter.chapter_number != ch_num:`
Even on Page 19, when `"Chapter 1"` appears, `current_chapter.chapter_number == 1`, so the parser drops it as a duplicate!

### 3.2. Why Only 1 Chunk Was Produced (The Catastrophic Aggregation Bug)
1. In `parser.py:125`, because no section numbers like `1.1` were found on Pages 1–18, every single line across all 20 pages was appended to `current_chapter.raw_intro_text`:
   ```python
   current_chapter.raw_intro_text += " " + line
   ```
2. In `parser.py:129-132`:
   ```python
   if not ch.sections and ch.raw_intro_text.strip():
       default_sec = ParsedSection(section_number=f"{ch.chapter_number}.1", title=ch.title, start_page=ch.start_page)
       default_sec.raw_text_blocks.append(ch.raw_intro_text.strip())
       ch.sections.append(default_sec)
   ```
   `default_sec.raw_text_blocks` received a **single element array** containing the entire 38,000-character concatenated text of all 20 pages!
3. In `chunker.py:47-87` (`SemanticChunker.chunk_section_text`):
   ```python
   for line in text_lines:
       line_str = line.strip()
       if (current_char_count >= cls.MIN_CHUNK_CHARS and is_special) or (current_char_count + len(line_str) > cls.MAX_CHUNK_CHARS):
           if current_paragraphs: # <-- EMPTY on iteration 1!
               ...
               chunks.append(...)
       current_paragraphs.append(line_str)
       current_char_count += len(line_str)
   ```
   `text_lines` contains only 1 string of length 38,000.
   - Iteration 1: `current_paragraphs` is empty, so no chunk is emitted. `current_paragraphs.append(line_str)` puts the entire 38,000-character line into `current_paragraphs`.
   - The loop finishes after 1 iteration!
   - Line 88 ("Flush remaining lines"):
     `combined = " ".join(current_paragraphs)` (all 38,000 characters)
     `chunks.append(RawChunkCandidate(chunk_text=combined, ...))`
   - Result: Exactly **1 chunk** with 38,000 characters and `page_number = 1`.

### 3.3. Why Only 2 Questions Were Generated
1. In `builder.py:88-106`, exactly 1 section was created (`"1.1 Class 8 Textbook"`).
2. `builder.py:109` called `ai_provider.extract_concepts_and_objectives("Class 8 Textbook", combined_sec_text)`.
3. In `mock_provider.py:412-433`, the extractor returns exactly **1 concept** for the section (`name="Class 8 Textbook"`).
4. In `question_generator.py:30-40`, the generator iterates over `concepts` (length = 1) and calls `generate_candidate_questions`.
5. In `mock_provider.py:441-474`, `generate_candidate_questions` returns exactly **2 questions** (1 MCQ + 1 Rubric question).
6. Result: Exactly **2 questions** for the entire 20-page document.

---

## 4. Proposed Parser & Ingestion Pipeline Improvements

### 4.1. Table of Contents (TOC) Detection & Extraction Engine
Add dedicated TOC analysis (`app/services/curriculum_ingestion/toc_extractor.py`):
- Scan pages for TOC signals: `"Contents"`, `"Table of Contents"`, `"Index"`, or sequences of `Chapter \d+ ... \d+` or `Unit \d+ ... \d+`.
- Extract structured TOC entries:
  ```python
  class TOCEntry:
      entry_type: str  # "chapter", "unit", "section", "front_matter"
      number: int
      title: str
      page_target: int
  ```
- In `curiosity.pdf`, Page 19 contains:
  - `Chapter 1: Exploring the Investigative World of Science (p. 1)`
  - `Chapter 2: The Invisible Living World: Beyond Our Naked Eye (p. 8)`
  - ...
  - `Chapter 13: Our Home: Earth, a Unique Life Sustaining Planet (p. 210)`
- If a document is a **Prelims / TOC document**:
  - Expose the catalogued chapters in metadata and curriculum database.
  - Tag the document confidence as `HIGH_TOC_CATALOG_ONLY` or `PRELIMS_DOCUMENT`.
  - Provide a warning: `"Prelims document detected. 13 syllabus chapters catalogued from Table of Contents; body pages are outside this document."`

### 4.2. Generalized Structural Hierarchy (Remove "Chapter X" Exclusivity)
Support diverse document hierarchy schemes:
1. **Chapter-based:** `Chapter 1`, `Chapter One`, `CHAPTER 1`, `Ch. 1`
2. **Unit-based:** `Unit 1`, `Unit I`, `UNIT 1: MATTER`
3. **Lesson/Module-based:** `Lesson 1`, `Module 1`, `Part 1`
4. **Numbered-Sections:** `1. Introduction`, `1.1 Scientific Inquiry`, `1.2 Background`
5. **Semantic Front Matter:** `Foreword`, `About this Book`, `Acknowledgements`, `Constitution of India`

### 4.3. Multi-Signal Heading Detection
Combine multiple signals rather than regex-only:
- Line length ($\le 60$ chars)
- Absence of terminal punctuation (no trailing period/semicolon)
- Leading numbering (`1.`, `1.1`, `Chapter 1`, `Unit 1`)
- Capitalization (Title Case or ALL CAPS)
- Surrounding blank line whitespace

### 4.4. Running Header & Footer Suppression
Implement a statistical n-gram / line frequency detector:
- Any line that appears on $\ge 3$ distinct pages with identical or near-identical text (e.g. `0_Prelims.indd...`, `Reprint 2026-27`, `Textbook Development Team`, `Curiosity Textbook of Science`) is classified as running header/footer and stripped from learning text.

### 4.5. Structural Confidence Tiers
Assign explicit structural confidence:
- **`HIGH`**: Document has clear explicit chapter/unit markers with matching section numbering.
- **`MEDIUM`**: Structure inferred from numbered headings (`1.1`, `1.2`) or clear TOC reconciliation.
- **`LOW` ("Structure requires review")**: Document has no standard structure (e.g., front-matter only, or unnumbered notes). Admin dashboard highlights: `"Structure requires review"`.

### 4.6. Intelligent Fallback ("Unclassified / Needs Review")
If no chapters/units are detected:
- Rather than dumping 20 pages into a single fake chapter, partition the document by logical front-matter headings (`Foreword`, `About this Book`, `Table of Contents`, `Constitution of India`).
- If completely unclassifiable, group by 3–5 page semantic clusters labeled `Section 1 (Pages 1–5)`, `Section 2 (Pages 6–10)`, etc., marked as `"Unclassified / Needs Review"`.

### 4.7. Robust Paragraph-Aware Semantic Chunking
Fix `SemanticChunker.chunk_section_text`:
- Split input into real paragraphs (`\n\n` or line sequences).
- If any single block exceeds `MAX_CHUNK_CHARS` (1,000 chars), subdivide on sentence boundaries (`[.!?]\s+`), never emitting multi-thousand-character monster chunks.
- For a 20-page document with ~38,000 characters, target **25–40 cohesive chunks** (each 500–1,000 characters), correctly tagged with their individual `page_number`.

### 4.8. Scaled & Incremental Question Generation
- Generate questions for all extracted concepts (not just 1 concept).
- For documents with multiple concepts, generate 3–5 questions per concept across Bloom cognitive levels.
- Non-blocking isolation: If question generation fails or is deferred, chunks and curriculum remain valid and reviewable.

### 4.9. Sanity Checks & Content Metrics
In `pipeline.py`:
- Sanity Check 1: If `page_count > 10` and `chunks_count < 3` $\implies$ add warning: `"Unusually low chunk count. Review extraction."`
- Sanity Check 2: If `page_count > 10` and `questions_count < 5` $\implies$ add warning: `"Low question coverage."`
- Sanity Check 3: If `toc_detected == True` and `body_page_count == 0` $\implies$ add warning: `"Prelims/TOC document detected without main textbook chapters."`
- Store rich metrics in `metrics_json`: `pages_count`, `extracted_chars`, `paragraphs_count`, `headings_count`, `chapters_count`, `sections_count`, `topics_count`, `concepts_count`, `chunks_count`, `questions_count`, `confidence_level`.

### 4.10. Admin Inspector UI Enhancements
In `frontend/src/app/admin/page.tsx`:
- Render an **Extraction Summary Card**:
  - Pages, Chapters, Sections, Topics, Concepts, Chunks, Questions, Confidence (`HIGH`, `MEDIUM`, `LOW`).
  - Prominently render sanity warnings in amber/red alert boxes.
  - Allow admin/parent to inspect and review structure before clicking **Publish**.
