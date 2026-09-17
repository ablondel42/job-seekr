"""Tests for ReportLab ATS-friendly PDF generation."""

from pathlib import Path
from src.pdf_generator import PDFGenerator, _sanitize_inline_markdown


def test_sanitize_inline_markdown():
    """Verify markdown to HTML/XML tag conversion and escaping."""
    raw = "Skills in **Python** & *SQL*, plus `git` & <scripts>"
    sanitized = _sanitize_inline_markdown(raw)
    assert "<b>Python</b>" in sanitized
    assert "<i>SQL</i>" in sanitized
    assert '<font face="Courier">git</font>' in sanitized
    assert "&amp;" in sanitized
    assert "&lt;scripts&gt;" in sanitized


def test_generate_pdf_file(tmp_path):
    """Verify generating a valid PDF file with standard headers and sections."""
    pdf_gen = PDFGenerator()
    out_pdf = tmp_path / "test_resume.pdf"

    markdown_content = """# John Test
**Staff Software Engineer**  
Email: john@test.com | Location: Remote  

---

## Experience
### Tech Corp - Staff Engineer
- Built high throughput services in Python.
- Spearheaded LLM integration.

## Education
**B.S. in Computer Science**
"""

    result_path = pdf_gen.markdown_to_pdf(markdown_content, out_pdf, title="Test Resume")
    assert result_path.exists()
    assert result_path.stat().st_size > 500

    # Verify standard PDF magic header '%PDF-'
    with open(result_path, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-"
