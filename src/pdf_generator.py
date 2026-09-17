"""Pure-Python ATS-friendly PDF generator using ReportLab Platypus."""

import html
import re
from pathlib import Path
from typing import List, Union

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from src.logger import get_logger

logger = get_logger("pdf_generator")


def _sanitize_inline_markdown(text: str) -> str:
    """Converts inline markdown (bold, italic, links) to ReportLab XML tags while escaping raw XML entities."""
    # First escape literal XML entities
    # But preserve our replacements
    text = html.escape(text, quote=False)

    # Convert **bold** or __bold__ to <b>bold</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)

    # Convert *italic* or _italic_ to <i>italic</i>
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<i>\1</i>", text)

    # Convert `code` to <font face="Courier">code</font>
    text = re.sub(r"`(.+?)`", r'<font face="Courier">\1</font>', text)

    # Convert [text](url) to text (url) or clickable link
    text = re.sub(r"\[(.+?)\]\((https?://[^\s)]+)\)", r'<u><link href="\2">\1</link></u>', text)

    return text


class PDFGenerator:
    """Compiles Markdown text into clean, modern, ATS-friendly PDF documents."""

    def __init__(self):
        self._init_styles()

    def _init_styles(self) -> None:
        """Sets up typographical hierarchy and colors."""
        base_styles = getSampleStyleSheet()

        # Primary palette
        primary_color = colors.HexColor("#1a202c")     # Dark Charcoal
        accent_color = colors.HexColor("#2b6cb0")      # Corporate Blue
        text_color = colors.HexColor("#2d3748")        # Body text dark slate
        meta_color = colors.HexColor("#4a5568")        # Subtitle/date grey

        self.style_name = ParagraphStyle(
            "DocName",
            parent=base_styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=primary_color,
            spaceAfter=2,
            alignment=0,  # Left aligned
        )

        self.style_contact = ParagraphStyle(
            "DocContact",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=meta_color,
            spaceAfter=6,
        )

        self.style_h2 = ParagraphStyle(
            "DocH2",
            parent=base_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=accent_color,
            spaceBefore=8,
            spaceAfter=2,
            keepWithNext=True,
        )

        self.style_h3 = ParagraphStyle(
            "DocH3",
            parent=base_styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13.5,
            textColor=primary_color,
            spaceBefore=5,
            spaceAfter=2,
            keepWithNext=True,
        )

        self.style_body = ParagraphStyle(
            "DocBody",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=text_color,
            spaceBefore=2,
            spaceAfter=3,
        )

        self.style_bullet = ParagraphStyle(
            "DocBullet",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=text_color,
            leftIndent=14,
            firstLineIndent=-10,
            spaceBefore=1,
            spaceAfter=1.5,
        )

    def markdown_to_pdf(
        self,
        markdown_text: str,
        output_path: Union[str, Path],
        title: str = "Application Document",
    ) -> Path:
        """Converts Markdown text into a clean ATS-friendly PDF file."""
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # 0.6 inch margins
        doc = SimpleDocTemplate(
            str(out_file),
            pagesize=letter,
            leftMargin=0.6 * inch,
            rightMargin=0.6 * inch,
            topMargin=0.6 * inch,
            bottomMargin=0.6 * inch,
            title=title,
        )

        story: List[Any] = []
        lines = markdown_text.strip().splitlines()

        in_first_header = True

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                story.append(Spacer(1, 4))
                continue

            # Header 1: # Name
            if line.startswith("# "):
                content = _sanitize_inline_markdown(line[2:].strip())
                story.append(Paragraph(content, self.style_name))
                in_first_header = False
                continue

            # Horizontal rule: --- or ***
            if re.match(r"^(\-{3,}|\*{3,})$", line):
                story.append(Spacer(1, 2))
                story.append(
                    HRFlowable(
                        width="100%",
                        thickness=0.8,
                        color=colors.HexColor("#cbd5e0"),
                        spaceBefore=2,
                        spaceAfter=5,
                    )
                )
                continue

            # Header 2: ## Section Title
            if line.startswith("## "):
                section_title = line[3:].strip()
                content = _sanitize_inline_markdown(section_title.upper())
                story.append(Paragraph(content, self.style_h2))
                story.append(
                    HRFlowable(
                        width="100%",
                        thickness=0.6,
                        color=colors.HexColor("#e2e8f0"),
                        spaceBefore=1,
                        spaceAfter=4,
                    )
                )
                continue

            # Header 3: ### Subtitle / Role
            if line.startswith("### "):
                content = _sanitize_inline_markdown(line[4:].strip())
                story.append(Paragraph(content, self.style_h3))
                continue

            # Bullet items: - or *
            if re.match(r"^[\-\*]\s+", line):
                bullet_content = re.sub(r"^[\-\*]\s+", "", line).strip()
                safe_bullet = f"&bull; {_sanitize_inline_markdown(bullet_content)}"
                story.append(Paragraph(safe_bullet, self.style_bullet))
                continue

            # Contact / Subhead immediately following name
            if in_first_header:
                content = _sanitize_inline_markdown(line)
                story.append(Paragraph(content, self.style_contact))
                continue

            # General paragraph text
            content = _sanitize_inline_markdown(line)
            story.append(Paragraph(content, self.style_body))

        try:
            doc.build(story)
            logger.info(f"Successfully rendered ATS PDF: {out_file}")
            return out_file
        except Exception as e:
            logger.error(f"Error building PDF at {out_file}: {e}")
            raise
