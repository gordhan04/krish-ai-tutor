import re
from typing import List, Dict, Any, Optional, Tuple, Set
from app.services.curriculum_ingestion.extractor import ExtractedPage
from app.services.curriculum_ingestion.toc_detector import TOCDetector, TOCEntry
from app.services.curriculum_ingestion.header_footer_detector import HeaderFooterDetector
from app.services.curriculum_ingestion.page_mapper import PageMapper


class ParsedActivity:
    def __init__(
        self,
        number: str,
        title: str,
        instructions: str,
        expected_observation: Optional[str] = None,
        safety_notes: Optional[str] = None,
        pdf_page: int = 1,
        printed_page: Optional[int] = None,
        source_sequence: int = 0,
        section_number: Optional[str] = None,
    ):
        self.number = number.strip()
        self.title = title.strip()
        self.instructions = instructions.strip()
        self.expected_observation = expected_observation
        self.safety_notes = safety_notes
        self.pdf_page = pdf_page
        self.printed_page = printed_page
        self.source_sequence = source_sequence
        self.section_number = section_number

    def __getitem__(self, key: str) -> Any:
        if key == "number":
            if self.number.startswith("Activity "):
                return self.number[len("Activity "):].strip()
            return self.number
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def get(self, key: str, default=None) -> Any:
        try:
            return self[key]
        except (KeyError, AttributeError):
            return default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "instructions": self.instructions,
            "expected_observation": self.expected_observation,
            "safety_notes": self.safety_notes,
            "pdf_page": self.pdf_page,
            "printed_page": self.printed_page,
            "source_sequence": self.source_sequence,
            "section_number": self.section_number,
        }


class ParsedFigure:
    def __init__(
        self,
        number: str,
        caption: str,
        image_reference: Optional[str] = None,
        pdf_page: int = 1,
        printed_page: Optional[int] = None,
        source_sequence: int = 0,
        section_number: Optional[str] = None,
    ):
        self.number = number.strip()
        self.caption = caption.strip()
        self.image_reference = image_reference
        self.pdf_page = pdf_page
        self.printed_page = printed_page
        self.source_sequence = source_sequence
        self.section_number = section_number

    def __getitem__(self, key: str) -> Any:
        if key == "number":
            if self.number.startswith("Fig. "):
                return self.number[len("Fig. "):].strip()
            return self.number
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def get(self, key: str, default=None) -> Any:
        try:
            return self[key]
        except (KeyError, AttributeError):
            return default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "caption": self.caption,
            "image_reference": self.image_reference,
            "pdf_page": self.pdf_page,
            "printed_page": self.printed_page,
            "source_sequence": self.source_sequence,
            "section_number": self.section_number,
        }


class ParsedSection:
    def __init__(
        self,
        section_number: str,
        title: str,
        start_page: int,
        end_page: Optional[int] = None,
        start_printed_page: Optional[int] = None,
        end_printed_page: Optional[int] = None,
        source_sequence: int = 0,
    ):
        self.section_number = section_number
        self.title = title
        self.start_page = start_page
        self.end_page = end_page or start_page
        self.start_printed_page = start_printed_page
        self.end_printed_page = end_printed_page
        self.source_sequence = source_sequence
        self.raw_text_blocks: List[Tuple[int, str]] = []  # (pdf_page, text_line)
        self.activities: List[ParsedActivity] = []
        self.figures: List[ParsedFigure] = []
        self.tables: List[Dict[str, Any]] = []


class ParsedChapter:
    def __init__(
        self,
        chapter_number: int,
        title: str,
        start_page: int,
        end_page: Optional[int] = None,
        printed_start_page: Optional[int] = None,
        printed_end_page: Optional[int] = None,
        source_sequence: int = 0,
    ):
        self.chapter_number = chapter_number
        self.title = title
        self.start_page = start_page
        self.end_page = end_page or start_page
        self.printed_start_page = printed_start_page
        self.printed_end_page = printed_end_page
        self.source_sequence = source_sequence
        self.sections: List[ParsedSection] = []
        self.activities: List[ParsedActivity] = []
        self.figures: List[ParsedFigure] = []
        self.raw_intro_text: str = ""
        self.exercises: List[Dict[str, Any]] = []
        self.extended_learning: List[Dict[str, Any]] = []


class ParsedFrontMatter:
    def __init__(self, title: str, start_page: int, end_page: int):
        self.title = title
        self.start_page = start_page
        self.end_page = end_page
        self.text_blocks: List[Tuple[int, str]] = []


class DocumentParser:
    """
    Robust structural textbook parser supporting:
    - Non-contiguous chapters (e.g. 1, 2, 3, 4, 8, 9 in Part I volumes)
    - Front matter isolation (pages 1-12)
    - Numbered sections (1.1, 1.2, etc.)
    - Activities as first-class entities (Activity 1.1)
    - Figures and figure captions (Fig. 1.1(a))
    - Exercises and Extended Learning
    - Running header/footer artifact suppression
    """

    CHAPTER_PATTERNS = [
        r"(?:CHAPTER|Chapter)\s+(\d+|[IVXLCDM]+)[\s:\.\-]+([^\n\r]+)",
        r"(?:CHAPTER|Chapter)\s+(\d+)\s*\n+([A-Z\s]{3,60})",
        r"^(?:Unit|UNIT)\s+(\d+|[IVXLCDM]+)[\s:\.\-]+([^\n\r]+)",
    ]

    SECTION_PATTERN = re.compile(r"^(\d+\.\d+)\s+([A-Z0-9][^\n\r]+)")
    ACTIVITY_PATTERN = re.compile(r"(?:Activity|ACTIVITY)\s+(\d+\.\d+)[:\s\-]*([^\n\r]*)", re.IGNORECASE)
    FIGURE_PATTERN = re.compile(r"(?:Fig\.|Figure)\s+(\d+\.\d+(?:\s*\([a-z]\))?)[:\s\-]*([^\n\r]*)", re.IGNORECASE)
    EXERCISE_HEADER = re.compile(r"^(?:EXERCISES|Exercises|QUESTIONS|Questions)\b", re.IGNORECASE)
    EXTENDED_LEARNING_HEADER = re.compile(r"^(?:EXTENDED LEARNING|Extended Learning)\b", re.IGNORECASE)

    @classmethod
    def parse_pages(
        cls,
        pages: List[ExtractedPage],
        toc_entries: Optional[List[TOCEntry]] = None,
        fallback_title: str = "Class 8 Textbook",
        page_mapper: Optional[PageMapper] = None,
        return_full: bool = False,
    ) -> Any:
        """
        Parses extracted pages into structured chapters, sections, activities, and front matter.
        Returns:
            If return_full=True: (chapters, front_matter, warnings, parse_metadata).
            If return_full=False: (chapters, warnings) for backward compatibility.
        """
        warnings: List[str] = []
        if not pages:
            return ([], [], ["No pages provided to parser."], {}) if return_full else ([], ["No pages provided to parser."])

        # 1. Detect repeated running headers/footers to filter out
        repeated_lines = HeaderFooterDetector.detect_repeated_lines(pages)

        # 2. Detect TOC if not provided
        if toc_entries is None:
            toc_pages = TOCDetector.find_toc_pages(pages)
            if toc_pages:
                toc_entries = TOCDetector.parse_toc_entries(toc_pages)

        # Find front matter cutoff (at least after TOC pages)
        toc_page_nums = [e.toc_page for e in toc_entries] if toc_entries else []
        min_content_page = max(toc_page_nums) + 1 if toc_page_nums else 1

        # 3. Detect Chapter Boundaries
        chapter_starts: List[Tuple[int, int, str]] = []  # (chapter_num, start_pdf_page, title)

        if toc_entries:
            # Use TOC entries to locate chapter start pages
            for e in toc_entries:
                clean_e_title = re.sub(r'[^a-zA-Z]', '', e.title).upper()
                found_page = None

                # Search starting from min_content_page
                for p in pages:
                    if p.page_number < min_content_page:
                        continue
                    # Check first 5 lines for chapter title or explicit chapter header
                    first_lines = p.lines[:5]
                    first_combined = " ".join(first_lines)
                    clean_first = re.sub(r'[^a-zA-Z]', '', first_combined).upper()

                    # Match title
                    if clean_e_title and (clean_e_title in clean_first or (len(clean_e_title) > 6 and clean_e_title[:8] in clean_first)):
                        found_page = p.page_number
                        break

                    # Match section X.1
                    if any(re.match(rf'^{e.number}\.1\b', l.strip()) for l in first_lines):
                        found_page = p.page_number
                        break

                    # Match explicit Chapter X header
                    if any(re.match(rf'^(?:Chapter|CHAPTER)\s+{e.number}\b', l.strip()) for l in first_lines):
                        found_page = p.page_number
                        break

                if found_page:
                    chapter_starts.append((e.number, found_page, e.title))
                else:
                    warnings.append(f"TOC Chapter {e.number} ('{e.title}') start page could not be located.")

        # Fallback: scan for Chapter X patterns in page text if TOC matching found < 2 chapters
        if len(chapter_starts) < 2:
            seen_ch_nums = {c[0] for c in chapter_starts}
            for p in pages:
                if p.page_number < min_content_page:
                    continue
                for pat in cls.CHAPTER_PATTERNS:
                    match = re.search(pat, p.text, re.IGNORECASE)
                    if match:
                        raw_num = match.group(1).strip()
                        try:
                            ch_n = int(raw_num)
                        except ValueError:
                            ch_n = len(chapter_starts) + 1
                        if ch_n not in seen_ch_nums:
                            seen_ch_nums.add(ch_n)
                            ch_t = match.group(2).strip().title()
                            chapter_starts.append((ch_n, p.page_number, ch_t))
                            break

        # Sort chapter starts by page number
        chapter_starts.sort(key=lambda x: x[1])

        # If still no chapter found, create a fallback chapter
        if not chapter_starts:
            first_content_p = min_content_page if min_content_page <= len(pages) else 1
            chapter_starts.append((1, first_content_p, fallback_title))
            warnings.append("No explicit chapter headers detected; created default chapter container.")

        # 4. Front Matter handling
        first_ch_page = chapter_starts[0][1]
        front_matter: List[ParsedFrontMatter] = []
        if first_ch_page > 1:
            fm = ParsedFrontMatter(title="Front Matter", start_page=1, end_page=first_ch_page - 1)
            for p in pages:
                if p.page_number < first_ch_page:
                    for l in p.lines:
                        if not HeaderFooterDetector.is_artifact_line(l, repeated_lines):
                            fm.text_blocks.append((p.page_number, l))
            front_matter.append(fm)

        # 5. Initialize PageMapper if not provided
        if not page_mapper:
            candidates = [{"chapter_number": c[0], "start_page": c[1]} for c in chapter_starts]
            page_mapper = PageMapper.analyze_pages(pages, toc_entries=toc_entries, chapter_candidates=candidates)

        # 6. Parse Chapters, Sections, Activities, Figures, and Exercises
        chapters: List[ParsedChapter] = []
        seq = 1

        for i, (ch_num, start_p, title) in enumerate(chapter_starts):
            end_p = chapter_starts[i + 1][1] - 1 if i + 1 < len(chapter_starts) else len(pages)
            p_start = page_mapper.pdf_to_printed(start_p)
            p_end = page_mapper.pdf_to_printed(end_p)

            ch = ParsedChapter(
                chapter_number=ch_num,
                title=title,
                start_page=start_p,
                end_page=end_p,
                printed_start_page=p_start,
                printed_end_page=p_end,
                source_sequence=seq,
            )
            seq += 1

            # Pages belonging to this chapter
            ch_pages = [p for p in pages if start_p <= p.page_number <= end_p]
            current_section: Optional[ParsedSection] = None
            in_exercises = False
            in_extended_learning = False
            current_activity: Optional[ParsedActivity] = None

            for p in ch_pages:
                pr_page = page_mapper.pdf_to_printed(p.page_number)
                for line in p.lines:
                    # Skip artifact lines (running headers/footers)
                    if HeaderFooterDetector.is_artifact_line(line, repeated_lines):
                        continue

                    # Check for Extended Learning header
                    if cls.EXTENDED_LEARNING_HEADER.search(line):
                        in_extended_learning = True
                        in_exercises = False
                        ch.extended_learning.append({
                            "title": line.strip(),
                            "page": p.page_number,
                            "printed_page": pr_page,
                            "text": [],
                        })
                        continue

                    # Check for Exercise header
                    if cls.EXERCISE_HEADER.search(line):
                        in_exercises = True
                        in_extended_learning = False
                        ch.exercises.append({
                            "title": line.strip(),
                            "page": p.page_number,
                            "printed_page": pr_page,
                            "text": [],
                        })
                        continue

                    # Check for Section header
                    sec_match = cls.SECTION_PATTERN.match(line)
                    if sec_match:
                        in_exercises = False
                        in_extended_learning = False
                        sec_num = sec_match.group(1).strip()
                        sec_title = sec_match.group(2).strip()

                        if current_section:
                            current_section.end_page = p.page_number
                            current_section.end_printed_page = pr_page

                        current_section = ParsedSection(
                            section_number=sec_num,
                            title=sec_title,
                            start_page=p.page_number,
                            start_printed_page=pr_page,
                            source_sequence=seq,
                        )
                        seq += 1
                        ch.sections.append(current_section)
                        continue

                    # Check for Activity
                    act_match = cls.ACTIVITY_PATTERN.search(line)
                    if act_match:
                        act_num = act_match.group(1).strip()
                        act_title = act_match.group(2).strip() or f"Activity {act_num}"
                        current_activity = ParsedActivity(
                            number=f"Activity {act_num}",
                            title=act_title,
                            instructions=line.strip(),
                            pdf_page=p.page_number,
                            printed_page=pr_page,
                            source_sequence=seq,
                            section_number=current_section.section_number if current_section else None,
                        )
                        seq += 1
                        ch.activities.append(current_activity)
                        if current_section:
                            current_section.activities.append(current_activity)

                    # Check for Figure
                    fig_match = cls.FIGURE_PATTERN.search(line)
                    if fig_match:
                        fig_num = fig_match.group(1).strip()
                        fig_cap = fig_match.group(2).strip() or line.strip()
                        fig_obj = ParsedFigure(
                            number=f"Fig. {fig_num}",
                            caption=fig_cap,
                            pdf_page=p.page_number,
                            printed_page=pr_page,
                            source_sequence=seq,
                            section_number=current_section.section_number if current_section else None,
                        )
                        seq += 1
                        ch.figures.append(fig_obj)
                        if current_section:
                            current_section.figures.append(fig_obj)

                    # Append content lines to appropriate container
                    if in_extended_learning and ch.extended_learning:
                        ch.extended_learning[-1]["text"].append(line)
                    elif in_exercises and ch.exercises:
                        ch.exercises[-1]["text"].append(line)
                    elif current_section:
                        current_section.raw_text_blocks.append((p.page_number, line))
                        if current_activity and current_activity.pdf_page == p.page_number:
                            current_activity.instructions += " " + line
                    else:
                        ch.raw_intro_text += " " + line

            # Finalize last section end page
            if current_section:
                current_section.end_page = end_p
                current_section.end_printed_page = p_end

            # Ensure chapter has at least one section
            if not ch.sections:
                default_sec = ParsedSection(
                    section_number=f"{ch.chapter_number}.1",
                    title=ch.title,
                    start_page=start_p,
                    end_page=end_p,
                    start_printed_page=p_start,
                    end_printed_page=p_end,
                    source_sequence=seq,
                )
                seq += 1
                if ch.raw_intro_text:
                    default_sec.raw_text_blocks.append((start_p, ch.raw_intro_text))
                ch.sections.append(default_sec)

            chapters.append(ch)

        # 7. Check for Non-Contiguous Chapter Sequences (e.g. 1, 2, 3, 4, 8, 9)
        ch_numbers = [c.chapter_number for c in chapters]
        is_contiguous = ch_numbers == list(range(min(ch_numbers), max(ch_numbers) + 1)) if ch_numbers else True
        if not is_contiguous:
            missing = set(range(min(ch_numbers), max(ch_numbers) + 1)) - set(ch_numbers)
            status_desc = "VALID NON-CONTIGUOUS VOLUME"
            warnings.append(
                f"Non-contiguous chapter sequence detected: {ch_numbers}. Missing from continuous range: {sorted(missing)}. "
                f"Status: {status_desc} (Part I / Multi-part curriculum document)."
            )
        else:
            status_desc = "VALID CONTIGUOUS VOLUME"

        metadata = {
            "chapter_count": len(chapters),
            "chapter_numbers": ch_numbers,
            "volume_status": status_desc,
            "front_matter_pages": first_ch_page - 1,
            "content_pages": len(pages) - (first_ch_page - 1),
            "page_offset": page_mapper.offset,
            "total_activities": sum(len(c.activities) for c in chapters),
            "total_figures": sum(len(c.figures) for c in chapters),
            "total_sections": sum(len(c.sections) for c in chapters),
        }

        if return_full:
            return chapters, front_matter, warnings, metadata
        return chapters, warnings
