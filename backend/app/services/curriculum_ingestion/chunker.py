import re
from typing import List, Dict, Any, Optional


class RawChunkCandidate:
    def __init__(
        self,
        chunk_text: str,
        content_type: str,
        page_number: int,
        section_number: Optional[str] = None,
    ):
        self.chunk_text = chunk_text.strip()
        self.content_type = content_type
        self.page_number = page_number
        self.section_number = section_number


class SemanticChunker:
    """
    Splits curriculum text into semantically cohesive retrieval chunks,
    preserving definitions, worked examples, activities, and tables.
    """

    MIN_CHUNK_CHARS = 100
    MAX_CHUNK_CHARS = 1000

    @classmethod
    def classify_content_type(cls, text: str) -> str:
        """Determines the pedagogical content type of a block."""
        lower = text.lower()
        if any(w in lower for w in ["definition", "is defined as", "is called", "we mean by"]):
            return "definition"
        if any(w in lower for w in ["activity", "experiment", "take a beaker", "test whether", "procedure"]):
            return "experiment"
        if any(w in lower for w in ["example", "for instance", "such as"]):
            return "example"
        if any(w in lower for w in ["what you have learnt", "summary", "in a nutshell", "key points"]):
            return "summary"
        if any(w in lower for w in ["exercises", "questions", "fill in the blanks", "answer the following"]):
            return "exercise"
        if any(w in lower for w in ["table ", "tabulate", "col 1", "column"]):
            return "table"
        return "explanation"

    @classmethod
    def chunk_section_text(
        cls,
        text_lines: List[str],
        start_page: int,
        section_number: str,
    ) -> List[RawChunkCandidate]:
        """
        Groups lines into natural paragraphs and semantic chunks.
        """
        if not text_lines:
            return []

        chunks: List[RawChunkCandidate] = []
        current_paragraphs: List[str] = []
        current_char_count = 0

        for line in text_lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Detect if this line starts a new distinct unit like Activity or Exercise
            is_special = bool(re.match(r"^(?:Activity|ACTIVITY|Fig\.|Figure|Table|TABLE|Exercise)", line_str))

            if (current_char_count >= cls.MIN_CHUNK_CHARS and is_special) or (current_char_count + len(line_str) > cls.MAX_CHUNK_CHARS):
                if current_paragraphs:
                    combined = " ".join(current_paragraphs)
                    c_type = cls.classify_content_type(combined)
                    chunks.append(RawChunkCandidate(
                        chunk_text=combined,
                        content_type=c_type,
                        page_number=start_page,
                        section_number=section_number,
                    ))
                    current_paragraphs = []
                    current_char_count = 0

            current_paragraphs.append(line_str)
            current_char_count += len(line_str)

        # Flush remaining lines
        if current_paragraphs:
            combined = " ".join(current_paragraphs)
            if len(combined) >= 40:
                c_type = cls.classify_content_type(combined)
                chunks.append(RawChunkCandidate(
                    chunk_text=combined,
                    content_type=c_type,
                    page_number=start_page,
                    section_number=section_number,
                ))

        return chunks
