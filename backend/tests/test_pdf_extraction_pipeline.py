import pytest
from app.services.curriculum_ingestion.extractor import PDFExtractor
from app.services.curriculum_ingestion.parser import DocumentParser
from app.services.curriculum_ingestion.chunker import SemanticChunker
from tests.fixtures.ncert_pdf_generator import generate_class_8_combustion_textbook_pdf, create_simple_pdf


def test_pdf_extraction_page_preservation():
    """Verifies that PDFExtractor accurately extracts all pages and verifies selectable text."""
    pdf_bytes = generate_class_8_combustion_textbook_pdf()
    pages, requires_ocr, warnings = PDFExtractor.extract_from_bytes(pdf_bytes)

    assert len(pages) == 4
    assert requires_ocr is False
    assert len(warnings) == 0

    assert pages[0].page_number == 1
    assert "Combustion and Flame" in pages[0].text
    assert pages[1].page_number == 2
    assert "HOW DO WE CONTROL FIRE" in pages[1].text
    assert pages[2].page_number == 3
    assert "TYPES OF COMBUSTION" in pages[2].text
    assert pages[3].page_number == 4
    assert "EXERCISES" in pages[3].text


def test_scanned_pdf_detected_as_ocr_required():
    """Verifies that PDFs with insufficient selectable text are flagged for OCR."""
    # Create a PDF with empty / low-density text
    empty_pdf = create_simple_pdf([[" "], ["   "]])
    pages, requires_ocr, warnings = PDFExtractor.extract_from_bytes(empty_pdf)

    assert requires_ocr is True
    assert any("OCR" in w for w in warnings)


def test_structural_chapter_and_section_parsing():
    """Verifies deterministic detection of chapters, sections, and activities."""
    pdf_bytes = generate_class_8_combustion_textbook_pdf()
    pages, _, _ = PDFExtractor.extract_from_bytes(pdf_bytes)

    chapters, warnings = DocumentParser.parse_pages(pages)

    assert len(chapters) == 1
    ch = chapters[0]
    assert ch.chapter_number == 4
    assert "Combustion And Flame" in ch.title
    assert ch.start_page == 1

    # Check sections
    sec_numbers = [s.section_number for s in ch.sections]
    assert "4.1" in sec_numbers
    assert "4.2" in sec_numbers
    assert "4.3" in sec_numbers
    assert "4.4" in sec_numbers
    assert "4.5" in sec_numbers
    assert "4.6" in sec_numbers

    # Check activity detection in section 4.1
    sec_41 = next(s for s in ch.sections if s.section_number == "4.1")
    assert len(sec_41.activities) >= 1
    assert sec_41.activities[0]["number"] == "4.1"


def test_semantic_chunker_content_types_and_citations():
    """Verifies that chunks retain page citations and appropriate pedagogical content types."""
    lines = [
        "A chemical process in which a substance reacts with oxygen to give off heat is called combustion.",
        "The substance that undergoes combustion is said to be combustible. It is also called a fuel.",
        "Activity 4.1: Take a piece of charcoal and hold it near a flame. What do you observe?",
        "Charcoal burns in air producing heat and carbon dioxide.",
    ]
    chunks = SemanticChunker.chunk_section_text(lines, start_page=1, section_number="4.1")
    assert len(chunks) >= 1

    # Check that at least one definition or experiment is classified
    content_types = [c.content_type for c in chunks]
    assert any(t in ("definition", "experiment", "explanation") for t in content_types)
    for c in chunks:
        assert c.page_number == 1
        assert len(c.chunk_text) >= 40
