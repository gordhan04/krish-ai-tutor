import re
from typing import List, Dict, Any, Optional, Tuple
from app.services.curriculum_ingestion.extractor import ExtractedPage


class ParsedSection:
    def __init__(self, section_number: str, title: str, start_page: int):
        self.section_number = section_number
        self.title = title
        self.start_page = start_page
        self.raw_text_blocks: List[str] = []
        self.activities: List[Dict[str, Any]] = []
        self.tables: List[Dict[str, Any]] = []
        self.figures: List[Dict[str, Any]] = []


class ParsedChapter:
    def __init__(self, chapter_number: int, title: str, start_page: int):
        self.chapter_number = chapter_number
        self.title = title
        self.start_page = start_page
        self.sections: List[ParsedSection] = []
        self.raw_intro_text: str = ""
        self.exercises: List[str] = []


class DocumentParser:
    """
    Deterministic structural parser for school textbooks (NCERT Class 8 patterns).
    Identifies chapters, sections, activities, exercises, tables, and figures.
    """

    CHAPTER_PATTERNS = [
        # e.g., "Chapter 4: Combustion and Flame" or "CHAPTER 11 - CHEMICAL EFFECTS"
        r"(?:CHAPTER|Chapter)\s+(\d+|[IVXLCDM]+)[\s:\.\-]+([^\n\r]+)",
        # e.g., "CHAPTER 4\nCOMBUSTION AND FLAME"
        r"(?:CHAPTER|Chapter)\s+(\d+)\s*\n+([A-Z\s]{3,50})",
    ]

    SECTION_PATTERN = r"^(\d+\.\d+)\s+([A-Z0-9][^\n\r]+)"
    ACTIVITY_PATTERN = r"(?:Activity|ACTIVITY)\s+(\d+\.\d+)[:\s\-]+([^\n\r]+)"
    EXERCISE_PATTERN = r"(?:EXERCISES|Exercises|QUESTIONS|Questions)\s*\n"
    FIGURE_PATTERN = r"(?:Fig\.|Figure|FIGURE)\s+(\d+\.\d+)[:\s\-]+([^\n\r]+)"
    TABLE_PATTERN = r"(?:Table|TABLE)\s+(\d+\.\d+)[:\s\-]+([^\n\r]+)"

    @classmethod
    def parse_pages(cls, pages: List[ExtractedPage], fallback_title: str = "Class 8 Textbook") -> Tuple[List[ParsedChapter], List[str]]:
        """
        Parses extracted pages into structured chapters, sections, and pedagogical units.
        Returns (chapters, warnings).
        """
        warnings = []
        full_text_by_page = {p.page_number: p.text for p in pages if p.text}
        
        if not full_text_by_page:
            return [], ["No text available across all pages to parse."]

        chapters: List[ParsedChapter] = []
        current_chapter: Optional[ParsedChapter] = None
        current_section: Optional[ParsedSection] = None

        for p in pages:
            lines = p.lines
            page_num = p.page_number
            page_text = p.text

            # Check if this page introduces a new chapter
            chapter_matched = False
            for pattern in cls.CHAPTER_PATTERNS:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    raw_num = match.group(1).strip()
                    ch_title = match.group(2).strip().title()
                    # Convert Roman numerals if necessary
                    try:
                        ch_num = int(raw_num)
                    except ValueError:
                        roman_map = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15, "XVI": 16}
                        ch_num = roman_map.get(raw_num.upper(), len(chapters) + 1)

                    # Avoid duplicate chapter detections on the same chapter
                    if not current_chapter or current_chapter.chapter_number != ch_num:
                        current_chapter = ParsedChapter(chapter_number=ch_num, title=ch_title, start_page=page_num)
                        chapters.append(current_chapter)
                        current_section = None
                        chapter_matched = True
                        break

            # If no chapter detected yet, initialize a fallback chapter
            if not current_chapter:
                current_chapter = ParsedChapter(chapter_number=1, title=fallback_title, start_page=page_num)
                chapters.append(current_chapter)
                warnings.append("No explicit 'Chapter X' header detected; created default chapter container.")

            # Look for Section headers and content
            for line in lines:
                sec_match = re.match(cls.SECTION_PATTERN, line)
                if sec_match:
                    sec_num = sec_match.group(1).strip()
                    sec_title = sec_match.group(2).strip()
                    current_section = ParsedSection(section_number=sec_num, title=sec_title, start_page=page_num)
                    current_chapter.sections.append(current_section)
                    continue

                act_match = re.search(cls.ACTIVITY_PATTERN, line)
                if act_match and current_section:
                    current_section.activities.append({
                        "number": act_match.group(1).strip(),
                        "title": act_match.group(2).strip(),
                        "page": page_num,
                    })

                fig_match = re.search(cls.FIGURE_PATTERN, line)
                if fig_match and current_section:
                    current_section.figures.append({
                        "number": fig_match.group(1).strip(),
                        "caption": fig_match.group(2).strip(),
                        "page": page_num,
                    })

                # Append line to active section or chapter intro
                if current_section:
                    current_section.raw_text_blocks.append(line)
                else:
                    current_chapter.raw_intro_text += " " + line

        # If a chapter has no sections, create a default section from intro
        for ch in chapters:
            if not ch.sections and ch.raw_intro_text.strip():
                default_sec = ParsedSection(section_number=f"{ch.chapter_number}.1", title=ch.title, start_page=ch.start_page)
                default_sec.raw_text_blocks.append(ch.raw_intro_text.strip())
                ch.sections.append(default_sec)

        return chapters, warnings
