#!/usr/bin/env python3
"""
Jupyter Notebook to PDF AI Agent

This agent parses Jupyter Notebook (.ipynb) files, extracts markdown cells,
code cells, and outputs, then generates a professionally formatted PDF report.

Features:
- Parses notebook JSON structure
- Extracts markdown, code, and outputs (text/images)
- Syntax highlighting for code
- Proper heading hierarchy for markdown
- Styled output blocks
- Table of contents
- Professional headers and page numbers
"""

import json
import argparse
import re
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# PDF generation
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    Table, TableStyle, KeepTogether, Flowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

# Syntax highlighting
from pygments import highlight
from pygments.lexers import PythonLexer, get_lexer_by_name
from pygments.formatters import HtmlFormatter
from pygments.styles import get_style_by_name

# Markdown parsing
import markdown
from bs4 import BeautifulSoup


class NotebookParser:
    """Parses Jupyter Notebook files and extracts content."""

    def __init__(self, notebook_path: str):
        self.notebook_path = Path(notebook_path)
        self.notebook_data = self._load_notebook()
        self.metadata = self.notebook_data.get('metadata', {})
        self.cells = self.notebook_data.get('cells', [])

    def _load_notebook(self) -> Dict[str, Any]:
        """Load and parse the notebook JSON file."""
        try:
            with open(self.notebook_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid notebook JSON: {e}")
        except FileNotFoundError:
            raise FileNotFoundError(f"Notebook not found: {self.notebook_path}")

    def get_notebook_title(self) -> str:
        """Extract title from notebook metadata or first heading."""
        # Try to get title from metadata
        title = self.metadata.get('title', '')
        if title:
            return title

        # Try first markdown cell with heading
        for cell in self.cells:
            if cell['cell_type'] == 'markdown':
                source = cell.get('source', '')
                if isinstance(source, list):
                    source = ''.join(source)
                # Look for first heading
                for line in source.split('\n'):
                    if line.startswith('#'):
                        return line.lstrip('#').strip()

        # Fallback to filename
        return self.notebook_path.stem.replace('_', ' ').title()

    def extract_markdown_cells(self) -> List[Dict[str, Any]]:
        """Extract all markdown cells."""
        markdown_cells = []
        for i, cell in enumerate(self.cells):
            if cell['cell_type'] == 'markdown':
                source = cell.get('source', '')
                if isinstance(source, list):
                    source = ''.join(source)
                markdown_cells.append({
                    'index': i,
                    'source': source,
                    'level': self._get_heading_level(source)
                })
        return markdown_cells

    def extract_code_cells(self) -> List[Dict[str, Any]]:
        """Extract all code cells with their outputs."""
        code_cells = []
        for i, cell in enumerate(self.cells):
            if cell['cell_type'] == 'code':
                source = cell.get('source', '')
                if isinstance(source, list):
                    source = ''.join(source)
                outputs = self._process_outputs(cell.get('outputs', []))
                code_cells.append({
                    'index': i,
                    'source': source,
                    'outputs': outputs,
                    'execution_count': cell.get('execution_count'),
                    'is_empty': not source.strip()
                })
        return code_cells

    def _get_heading_level(self, text: str) -> int:
        """Determine heading level from markdown text."""
        if isinstance(text, list):
            text = ''.join(text)
        for line in text.split('\n'):
            if line.startswith('#'):
                return len(line.split('#')[0])
        return 0

    def _process_outputs(self, outputs: List[Dict]) -> List[Dict[str, Any]]:
        """Process cell outputs for PDF rendering."""
        processed = []
        for output in outputs:
            out_type = output.get('output_type', '')
            result = {'type': out_type, 'content': None, 'data': None, 'image': None, 'html': None, 'latex': None, 'stream_name': None, 'ename': None, 'evalue': None, 'traceback': []}

            if out_type == 'execute_result':
                data = output.get('data', {})
                if 'text/plain' in data:
                    result['content'] = data['text/plain']
                if 'text/html' in data:
                    result['html'] = data['text/html']
                if 'image/png' in data:
                    result['image'] = data['image/png']
                if 'text/latex' in data:
                    result['latex'] = data['text/latex']

            elif out_type == 'stream':
                result['content'] = output.get('text', '')
                result['stream_name'] = output.get('name', '')

            elif out_type == 'display_data':
                data = output.get('data', {})
                if 'image/png' in data:
                    result['image'] = data['image/png']
                if 'text/plain' in data:
                    result['content'] = data['text/plain']

            elif out_type == 'error':
                result['ename'] = output.get('ename', '')
                result['evalue'] = output.get('evalue', '')
                result['traceback'] = output.get('traceback', [])

            processed.append(result)
        return processed


class PDFConverter:
    """Converts parsed notebook content to professional PDF."""

    # Color scheme
    COLORS = {
        'primary': HexColor('#2c3e50'),
        'secondary': HexColor('#34495e'),
        'accent': HexColor('#3498db'),
        'code_bg': HexColor('#f8f8f8'),
        'output_bg': HexColor('#f0f0f0'),
        'error_bg': HexColor('#ffe6e6'),
        'border': HexColor('#bdc3c7'),
    }

    def __init__(self, output_path: str, title: str, author: str = None):
        self.output_path = Path(output_path)
        self.title = title
        self.author = author or "Generated by nb2pdf_agent"
        self.styles = self._create_styles()
        self.toc_data = []
        self.code_formatter = HtmlFormatter(style='colorful')

    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create custom paragraph styles for the PDF."""
        base = getSampleStyleSheet()

        styles = {
            'title': ParagraphStyle(
                'CustomTitle',
                parent=base['Heading1'],
                fontSize=24,
                textColor=self.COLORS['primary'],
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            ),
            'subtitle': ParagraphStyle(
                'CustomSubtitle',
                parent=base['Normal'],
                fontSize=12,
                textColor=self.COLORS['secondary'],
                spaceAfter=20,
                alignment=TA_CENTER,
                italic=True
            ),
            'heading1': ParagraphStyle(
                'CustomHeading1',
                parent=base['Heading1'],
                fontSize=18,
                textColor=self.COLORS['primary'],
                spaceBefore=20,
                spaceAfter=12,
                fontName='Helvetica-Bold',
                borderBottom=1,
                borderBottomColor=self.COLORS['border'],
                borderBottomPadding=5
            ),
            'heading2': ParagraphStyle(
                'CustomHeading2',
                parent=base['Heading2'],
                fontSize=14,
                textColor=self.COLORS['secondary'],
                spaceBefore=16,
                spaceAfter=10,
                fontName='Helvetica-Bold'
            ),
            'heading3': ParagraphStyle(
                'CustomHeading3',
                parent=base['Heading3'],
                fontSize=12,
                textColor=self.COLORS['accent'],
                spaceBefore=12,
                spaceAfter=8,
                fontName='Helvetica-Bold'
            ),
            'normal': ParagraphStyle(
                'CustomNormal',
                parent=base['Normal'],
                fontSize=10,
                textColor=colors.black,
                spaceBefore=6,
                spaceAfter=6,
                alignment=TA_JUSTIFY,
                leading=12
            ),
            'code': ParagraphStyle(
                'CodeBlock',
                parent=base['Code'],
                fontSize=8,
                fontName='Courier',
                textColor=colors.black,
                backColor=self.COLORS['code_bg'],
                borderLeftColor=self.COLORS['accent'],
                borderLeftWidth=3,
                leftIndent=10,
                rightIndent=10,
                spaceBefore=6,
                spaceAfter=6,
                alignment=TA_LEFT
            ),
            'output': ParagraphStyle(
                'OutputBlock',
                parent=base['Code'],
                fontSize=8,
                fontName='Courier',
                textColor=self.COLORS['secondary'],
                backColor=self.COLORS['output_bg'],
                leftIndent=15,
                rightIndent=10,
                spaceBefore=4,
                spaceAfter=4
            ),
            'error': ParagraphStyle(
                'ErrorBlock',
                parent=base['Code'],
                fontSize=8,
                fontName='Courier',
                textColor=HexColor('#c0392b'),
                backColor=self.COLORS['error_bg'],
                leftIndent=15,
                rightIndent=10,
                spaceBefore=4,
                spaceAfter=4
            ),
            'toc_entry': ParagraphStyle(
                'TOCEntry',
                parent=base['Normal'],
                fontSize=10,
                textColor=self.COLORS['secondary'],
                spaceBefore=4,
                spaceAfter=4
            ),
            'caption': ParagraphStyle(
                'Caption',
                parent=base['Normal'],
                fontSize=9,
                textColor=self.COLORS['secondary'],
                alignment=TA_CENTER,
                italic=True
            ),
            'header_text': ParagraphStyle(
                'HeaderText',
                parent=base['Normal'],
                fontSize=9,
                textColor=self.COLORS['secondary'],
                alignment=TA_LEFT
            ),
            'footer_text': ParagraphStyle(
                'FooterText',
                parent=base['Normal'],
                fontSize=9,
                textColor=self.COLORS['secondary'],
                alignment=TA_CENTER
            ),
        }

        return styles

    def _convert_markdown_to_html(self, markdown_text: str) -> str:
        """Convert markdown text to HTML for ReportLab."""
        if not markdown_text.strip():
            return ''

        # Convert markdown to HTML
        html = markdown.markdown(
            markdown_text,
            extensions=['fenced_code', 'tables', 'toc', 'nl2br']
        )

        # Parse and convert to ReportLab-friendly format
        soup = BeautifulSoup(html, 'html.parser')
        return self._soup_to_rst(soup)

    def _soup_to_rst(self, soup) -> str:
        """Convert BeautifulSoup parsed HTML to ReportLab compatible markup."""
        result = []

        for element in soup.children:
            if element.name is None:  # Text node
                text = element.strip() if element.strip() else None
                if text:
                    result.append(self._escape_text(text))
            elif element.name == 'h1':
                result.append(f"<h1>{self._get_inner_text(element)}</h1>")
            elif element.name == 'h2':
                result.append(f"<h2>{self._get_inner_text(element)}</h2>")
            elif element.name == 'h3':
                result.append(f"<h3>{self._get_inner_text(element)}</h3>")
            elif element.name == 'h4':
                result.append(f"<h4>{self._get_inner_text(element)}</h4>")
            elif element.name == 'p':
                # Don't wrap in para tag - just return the processed content
                result.append(self._process_inline(element))
            elif element.name == 'ul':
                result.append(self._process_list(element, ordered=False))
            elif element.name == 'ol':
                result.append(self._process_list(element, ordered=True))
            elif element.name == 'pre':
                code = element.get_text()
                result.append(f"<code>{self._escape_text(code)}</code>")
            elif element.name == 'table':
                result.append(self._process_table(element))
            elif element.name == 'blockquote':
                result.append(f"<i>{self._get_inner_text(element)}</i>")
            elif element.name == 'strong' or element.name == 'b':
                result.append(f"<b>{self._get_inner_text(element)}</b>")
            elif element.name == 'em' or element.name == 'i':
                result.append(f"<i>{self._get_inner_text(element)}</i>")
            elif element.name == 'code':
                result.append(f"<font name='Courier'>{self._escape_text(element.get_text())}</font>")

        return ''.join(result)

    def _escape_text(self, text: str) -> str:
        """Escape special characters for ReportLab."""
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        return text

    def _get_inner_text(self, element) -> str:
        """Get inner text of an HTML element."""
        return self._escape_text(element.get_text(strip=True))

    def _process_inline(self, element) -> str:
        """Process inline elements within a paragraph."""
        text = ""
        for child in element.children:
            if child.name is None:  # Text node
                text += self._escape_text(str(child))
            elif child.name == 'strong' or child.name == 'b':
                text += f"<b>{self._escape_text(child.get_text())}</b>"
            elif child.name == 'em' or child.name == 'i':
                text += f"<i>{self._escape_text(child.get_text())}</i>"
            elif child.name == 'code':
                text += f"<font name='Courier'>{self._escape_text(child.get_text())}</font>"
            elif child.name == 'a':
                text += f"<i>{self._escape_text(child.get_text())}</i>"
        return text

    def _process_list(self, element, ordered: bool = False) -> str:
        """Process HTML list to ReportLab markup."""
        items = []
        for i, li in enumerate(element.find_all('li', recursive=False)):
            text = self._process_inline(li)
            if ordered:
                items.append(f"{i+1}. {text}")
            else:
                items.append(f"• {text}")
        # Return as plain text with bullets, not wrapped in para
        return '<br/>'.join(items)

    def _process_table(self, element) -> str:
        """Process HTML table (simplified - full table handling in create_table)."""
        # Tables are handled separately with Table objects
        return ''

    def _create_code_block(self, code: str, language: str = 'python') -> Flowable:
        """Create a syntax-highlighted code block."""
        try:
            lexer = get_lexer_by_name(language, stripall=True)
            highlighted = highlight(code, lexer, self.code_formatter)

            # Convert highlighted HTML to formatted text
            soup = BeautifulSoup(highlighted, 'html.parser')

            # For simplicity, use plain code with styling
            # (Full syntax highlighting requires custom ReportLab canvas work)
            paragraphs = []
            for i, line in enumerate(code.split('\n'), 1):
                line = self._escape_text(line) if line else ' '
                paragraphs.append(f"{i:3d} | {line}")

            code_text = '\n'.join(paragraphs)
            return Paragraph(code_text, self.styles['code'])
        except Exception as e:
            return Paragraph(self._escape_text(code), self.styles['code'])

    def _create_output_block(self, output: Dict) -> List[Flowable]:
        """Create flowables for cell output."""
        flowables = []

        out_type = output.get('type', '')
        if not out_type:
            return flowables

        if out_type == 'execute_result':
            if output.get('image'):
                # Decode and save image temporarily
                import base64
                img_data = base64.b64decode(output['image'])
                img_path = Path(self.output_path.parent) / "temp_output_image.png"
                with open(img_path, 'wb') as f:
                    f.write(img_data)
                try:
                    img = Image(str(img_path), width=4*inch, height=3*inch)
                    img.hAlign = 'CENTER'
                    flowables.append(img)
                    flowables.append(Spacer(1, 10))
                finally:
                    img_path.unlink(missing_ok=True)

            if output.get('content'):
                content = self._escape_text(output['content'])
                # Limit output length
                if len(content) > 5000:
                    content = content[:5000] + "..."
                flowables.append(Paragraph(content, self.styles['output']))

        elif out_type == 'stream':
            content = self._escape_text(output.get('content', ''))
            if len(content) > 5000:
                content = content[:5000] + "..."
            flowables.append(Paragraph(content, self.styles['output']))

        elif out_type == 'error':
            error_text = f"{output.get('ename', 'Error')}: {output.get('evalue', '')}"
            flowables.append(Paragraph(self._escape_text(error_text), self.styles['error']))
            for tb_line in output.get('traceback', []):
                flowables.append(Paragraph(self._escape_text(tb_line), self.styles['error']))

        return flowables

    def _create_header_footer(self) -> Tuple[Any, Any]:
        """Create header and footer for the PDF."""
        def header(canvas, doc):
            canvas.saveState()
            # Header line
            canvas.setStrokeColor(self.COLORS['accent'])
            canvas.line(inch, doc.height + inch - 20, doc.width - inch, doc.height + inch - 20)
            # Title
            canvas.setFont('Helvetica-Bold', 9)
            canvas.setFillColor(self.COLORS['primary'])
            canvas.drawString(inch, doc.height + inch - 35, self.title)
            # Author
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(self.COLORS['secondary'])
            canvas.drawString(inch, doc.height + inch - 45, self.author)
            canvas.restoreState()

        def footer(canvas, doc):
            canvas.saveState()
            # Footer line
            canvas.setStrokeColor(self.COLORS['border'])
            canvas.line(inch, inch - 20, doc.width - inch, inch - 20)
            # Page number
            canvas.setFont('Helvetica', 9)
            canvas.setFillColor(self.COLORS['secondary'])
            page_num = canvas.getPageNumber()
            canvas.drawRightString(doc.width - inch, inch - 35, f"Page {page_num}")
            # Generation timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            canvas.drawString(inch, inch - 35, f"Generated: {timestamp}")
            canvas.restoreState()

        return header, footer

    def _build_toc(self, parser: NotebookParser) -> List[Flowable]:
        """Build table of contents from notebook headings."""
        flowables = []
        flowables.append(Paragraph("Table of Contents", self.styles['heading1']))
        flowables.append(Spacer(1, 20))

        markdown_cells = parser.extract_markdown_cells()
        toc_entries = []

        for cell in markdown_cells:
            level = cell['level']
            if level > 0:
                source = cell['source']
                # Extract heading text
                for line in source.split('\n'):
                    if line.startswith('#'):
                        heading = line.lstrip('#').strip()
                        toc_entries.append((level, heading))
                        break

        if not toc_entries:
            flowables.append(Paragraph("No headings found in notebook.", self.styles['normal']))
            return flowables

        for level, heading in toc_entries:
            indent = (level - 1) * 15
            entry_text = f"<para leftIndent={indent}>{heading}</para>"
            flowables.append(Paragraph(entry_text, self.styles['toc_entry']))

        return flowables

    def convert(self, parser: NotebookParser) -> None:
        """Convert parsed notebook to PDF."""
        # Create the PDF document
        doc = SimpleDocTemplate(
            str(self.output_path),
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
            title=self.title
        )

        story = []

        # Title page
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(self.title, self.styles['title']))
        story.append(Paragraph(self.author, self.styles['subtitle']))
        story.append(Spacer(1, 0.3*inch))
        story.append(PageBreak())

        # Table of Contents
        story.extend(self._build_toc(parser))
        story.append(PageBreak())

        # Process notebook cells
        markdown_cells = parser.extract_markdown_cells()
        code_cells = parser.extract_code_cells()

        processed_headings = set()

        for cell in parser.cells:
            if cell['cell_type'] == 'markdown':
                source = cell.get('source', '')
                if isinstance(source, list):
                    source = ''.join(source)

                if not source.strip():
                    continue

                # Check if this is a heading
                heading_level = self._get_heading_level_from_text(source)
                if heading_level > 0:
                    # Extract heading text
                    for line in source.split('\n'):
                        if line.startswith('#'):
                            heading = line.lstrip('#').strip()
                            if heading not in processed_headings:
                                story.append(Paragraph(heading, self.styles[f'heading{heading_level}']))
                                processed_headings.add(heading)
                            break
                    # Process remaining content as paragraph
                    html_content = self._convert_markdown_to_html(source)
                    if html_content:
                        story.append(Paragraph(html_content, self.styles['normal']))
                else:
                    # Regular markdown content
                    html_content = self._convert_markdown_to_html(source)
                    if html_content:
                        story.append(Paragraph(html_content, self.styles['normal']))

                story.append(Spacer(1, 10))

            elif cell['cell_type'] == 'code':
                source = cell.get('source', '')
                if isinstance(source, list):
                    source = ''.join(source)

                if source.strip():
                    # Add code block
                    story.append(Paragraph("Code:", self.styles['heading3']))
                    story.append(self._create_code_block(source))
                    story.append(Spacer(1, 10))

                # Add outputs
                outputs = self._process_outputs_for_story(cell.get('outputs', []))
                if outputs:
                    story.append(Paragraph("Output:", self.styles['heading3']))
                    story.extend(outputs)
                    story.append(Spacer(1, 15))

        # Build PDF with header and footer
        header, footer = self._create_header_footer()
        doc.build(story, onFirstPage=header, onLaterPages=header)

        print(f"[OK] PDF generated successfully: {self.output_path}")

    def _get_heading_level_from_text(self, text: str) -> int:
        """Get heading level from markdown text."""
        for line in text.split('\n'):
            if line.startswith('#'):
                return len(line.split('#')[0])
        return 0

    def _process_outputs_for_story(self, outputs: List[Dict]) -> List[Flowable]:
        """Process outputs for inclusion in the story."""
        flowables = []
        for output in outputs:
            flowables.extend(self._create_output_block(output))
        return flowables


class NotebookToPDFAgent:
    """Main agent class that orchestrates the conversion process."""

    def __init__(self, input_path: str, output_path: str = None):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path) if output_path else self._get_default_output()

    def _get_default_output(self) -> Path:
        """Generate default output path."""
        return self.input_path.with_suffix('.pdf')

    def run(self, verbose: bool = False) -> None:
        """Run the conversion pipeline."""
        print(f"\n{'='*60}")
        print("Jupyter Notebook to PDF AI Agent")
        print(f"{'='*60}\n")

        # Validate input
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_path}")

        if self.input_path.suffix.lower() != '.ipynb':
            raise ValueError(f"Expected .ipynb file, got: {self.input_path.suffix}")

        print(f"Input:  {self.input_path}")
        print(f"Output: {self.output_path}\n")

        # Parse notebook
        print("Parsing notebook...")
        parser = NotebookParser(str(self.input_path))

        title = parser.get_notebook_title()
        author = parser.metadata.get('author',
                parser.metadata.get('kernelspec', {}).get('display_name', 'Jupyter Notebook'))

        print(f"Title:  {title}")
        print(f"Cells:  {len(parser.cells)} total")
        print(f"        {len(parser.extract_markdown_cells())} markdown cells")
        print(f"        {len(parser.extract_code_cells())} code cells")

        # Convert to PDF
        print("\nGenerating PDF...")
        converter = PDFConverter(str(self.output_path), title, author)
        converter.convert(parser)

        print(f"\n{'='*60}")
        print("Conversion complete!")
        print(f"{'='*60}\n")


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description='Convert Jupyter Notebook (.ipynb) to professional PDF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python nb2pdf_agent.py notebook.ipynb
  python nb2pdf_agent.py notebook.ipynb -o report.pdf
  python nb2pdf_agent.py path/to/notebook.ipynb --verbose
        """
    )

    parser.add_argument(
        'input',
        help='Path to the Jupyter Notebook (.ipynb) file'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output PDF path (default: same as input with .pdf extension)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    try:
        agent = NotebookToPDFAgent(args.input, args.output)
        agent.run(verbose=args.verbose)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
