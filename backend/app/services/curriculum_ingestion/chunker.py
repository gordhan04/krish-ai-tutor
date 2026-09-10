import re
from typing import List, Dict, Any, Optional, Tuple
from app.services.curriculum_ingestion.page_mapper import PageMapper


class ContentType(str):
    """
    Case-insensitive, alias-aware content type representation.
    Supports canonical types (TEXT, ACTIVITY, DEFINITION, FIGURE, EXERCISE, etc.)
    while maintaining equality with legacy types ('experiment' == 'ACTIVITY', 'explanation' == 'TEXT').
    """
    def __eq__(self, other):
        if isinstance(other, str):
            s_up = self.upper()
            o_up = other.upper()
            if s_up == o_up:
                return True
            if (s_up in ("ACTIVITY", "EXPERIMENT")) and (o_up in ("ACTIVITY", "EXPERIMENT")):
                return True
            if (s_up in ("TEXT", "EXPLANATION")) and (o_up in ("TEXT", "EXPLANATION")):
                return True
        return super().__eq__(other)

    def __hash__(self):
        return hash(self.upper())


class RawChunkCandidate:
    def __init__(
        self,
        chunk_text: str,
        content_type: str,
        pdf_page_start: int,
        pdf_page_end: int,
        printed_page_start: Optional[int] = None,
        printed_page_end: Optional[int] = None,
        section_number: Optional[str] = None,
        chapter_number: Optional[int] = None,
        heading_path: Optional[str] = None,
        source_sequence: int = 0,
    ):
        self.chunk_text = chunk_text.strip()
        self.content_type = ContentType(content_type)
        self.pdf_page_start = pdf_page_start
        self.pdf_page_end = pdf_page_end
        self.printed_page_start = printed_page_start
        self.printed_page_end = printed_page_end
        self.section_number = section_number
        self.chapter_number = chapter_number
        self.heading_path = heading_path
        self.source_sequence = source_sequence

        # Backward compatibility alias
        self.page_number = pdf_page_start
        self.printed_page_number = printed_page_start


class SemanticChunker:
    """
    Hierarchical and semantic chunker for curriculum content.
    Maintains:
    Book -> Chapter -> Section -> Block -> Chunk
    Preserves exact PDF and printed page spans, content types, source ordering, and heading paths.
    """

    MIN_CHUNK_CHARS = 120
    MAX_CHUNK_CHARS = 950

    @classmethod
    def classify_content_type(cls, text: str) -> ContentType:
        """Determines the pedagogical content type of a block."""
        lower = text.lower()
        if any(w in lower for w in ["extended learning", "activities and projects", "field trip", "visit a farm"]):
            return ContentType("EXTENDED_LEARNING")
        if any(w in lower for w in ["exercises", "questions", "fill in the blanks", "answer the following", "match the following"]):
            return ContentType("EXERCISE")
        if any(w in lower for w in ["activity", "experiment", "take a beaker", "test whether", "procedure"]):
            return ContentType("ACTIVITY")
        if any(w in lower for w in ["definition", "is defined as", "is called", "we mean by", "means that"]):
            return ContentType("DEFINITION")
        if any(w in lower for w in ["fig.", "figure", "diagram", "illustration"]):
            return ContentType("FIGURE")
        if any(w in lower for w in ["for example", "for instance", "such as"]):
            return ContentType("EXAMPLE")
        if any(w in lower for w in ["what you have learnt", "summary", "in a nutshell", "key points"]):
            return ContentType("SUMMARY")
        if any(w in lower for w in ["table ", "tabulate"]):
            return ContentType("TABLE")
        if any(w in lower for w in ["caution", "danger", "hazard", "warning", "be careful"]):
            return ContentType("CAUTION")
        if any(w in lower for w in ["paheli and boojho", "boojho:", "paheli:"]):
            return ContentType("DIALOGUE")
        return ContentType("TEXT")

    @classmethod
    def chunk_section_blocks(
        cls,
        text_blocks: List[Tuple[int, str]],
        chapter_number: int,
        chapter_title: str,
        section_number: str,
        section_title: str,
        page_mapper: PageMapper,
        starting_sequence: int = 1,
    ) -> List[RawChunkCandidate]:
        """
        Groups section line blocks into natural paragraphs and semantic chunks.
        """
        if not text_blocks:
            return []

        chunks: List[RawChunkCandidate] = []
        current_paragraphs: List[str] = []
        current_char_count = 0
        min_p = text_blocks[0][0]
        max_p = text_blocks[0][0]
        seq = starting_sequence

        heading_path = f"Science > Grade 8 > Chapter {chapter_number}: {chapter_title} > {section_number} {section_title}"

        for p_num, line in text_blocks:
            line_str = line.strip()
            if not line_str:
                continue

            # Detect boundaries of activities, figures, questions
            is_special = bool(re.match(r"^(?:Activity|ACTIVITY|Fig\.|Figure|Table|TABLE|Exercise|\d+\.)", line_str))

            if (current_char_count >= cls.MIN_CHUNK_CHARS and is_special) or (current_char_count + len(line_str) > cls.MAX_CHUNK_CHARS):
                if current_paragraphs:
                    combined = " ".join(current_paragraphs)
                    c_type = cls.classify_content_type(combined)
                    chunks.append(RawChunkCandidate(
                        chunk_text=combined,
                        content_type=c_type,
                        pdf_page_start=min_p,
                        pdf_page_end=max_p,
                        printed_page_start=page_mapper.pdf_to_printed(min_p),
                        printed_page_end=page_mapper.pdf_to_printed(max_p),
                        section_number=section_number,
                        chapter_number=chapter_number,
                        heading_path=heading_path,
                        source_sequence=seq,
                    ))
                    seq += 1
                    current_paragraphs = []
                    current_char_count = 0
                    min_p = p_num

            current_paragraphs.append(line_str)
            current_char_count += len(line_str)
            max_p = p_num

        # Flush remaining lines
        if current_paragraphs:
            combined = " ".join(current_paragraphs)
            if len(combined) >= 40:
                c_type = cls.classify_content_type(combined)
                chunks.append(RawChunkCandidate(
                    chunk_text=combined,
                    content_type=c_type,
                    pdf_page_start=min_p,
                    pdf_page_end=max_p,
                    printed_page_start=page_mapper.pdf_to_printed(min_p),
                    printed_page_end=page_mapper.pdf_to_printed(max_p),
                    section_number=section_number,
                    chapter_number=chapter_number,
                    heading_path=heading_path,
                    source_sequence=seq,
                ))

        return chunks

    @classmethod
    def chunk_front_matter(
        cls,
        front_matter_blocks: List[Tuple[int, str]],
        page_mapper: PageMapper,
        starting_sequence: int = 1,
    ) -> List[RawChunkCandidate]:
        """Creates FRONT_MATTER chunks for TOC and prelims metadata."""
        if not front_matter_blocks:
            return []

        chunks: List[RawChunkCandidate] = []
        current_paragraphs: List[str] = []
        current_char_count = 0
        min_p = front_matter_blocks[0][0]
        max_p = front_matter_blocks[0][0]
        seq = starting_sequence

        heading_path = "Science > Grade 8 > Front Matter"

        for p_num, line in front_matter_blocks:
            line_str = line.strip()
            if not line_str:
                continue

            if current_char_count + len(line_str) > cls.MAX_CHUNK_CHARS:
                if current_paragraphs:
                    combined = " ".join(current_paragraphs)
                    chunks.append(RawChunkCandidate(
                        chunk_text=combined,
                        content_type="FRONT_MATTER",
                        pdf_page_start=min_p,
                        pdf_page_end=max_p,
                        printed_page_start=None,
                        printed_page_end=None,
                        section_number="FRONT_MATTER",
                        chapter_number=0,
                        heading_path=heading_path,
                        source_sequence=seq,
                    ))
                    seq += 1
                    current_paragraphs = []
                    current_char_count = 0
                    min_p = p_num

            current_paragraphs.append(line_str)
            current_char_count += len(line_str)
            max_p = p_num

        if current_paragraphs:
            combined = " ".join(current_paragraphs)
            if len(combined) >= 30:
                chunks.append(RawChunkCandidate(
                    chunk_text=combined,
                    content_type="FRONT_MATTER",
                    pdf_page_start=min_p,
                    pdf_page_end=max_p,
                    printed_page_start=None,
                    printed_page_end=None,
                    section_number="FRONT_MATTER",
                    chapter_number=0,
                    heading_path=heading_path,
                    source_sequence=seq,
                ))

        return chunks

    # Backward compatibility method for existing tests
    @classmethod
    def chunk_section_text(
        cls,
        text_lines: List[str],
        start_page: int,
        section_number: str,
    ) -> List[RawChunkCandidate]:
        blocks = [(start_page, l) for l in text_lines]
        dummy_mapper = PageMapper(offset=0, front_matter_end_pdf=0)
        return cls.chunk_section_blocks(
            text_blocks=blocks,
            chapter_number=1,
            chapter_title="General",
            section_number=section_number,
            section_title="General Section",
            page_mapper=dummy_mapper,
        )
