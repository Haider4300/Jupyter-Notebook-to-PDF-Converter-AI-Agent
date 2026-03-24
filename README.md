# Jupyter Notebook to PDF AI Agent
# Author: Ali Haider (AI-Data Engineer)

A professional AI-powered agent that converts Jupyter Notebooks (.ipynb) into beautifully formatted PDF reports. The agent intelligently extracts markdown cells, code cells, and outputs, then generates a polished, submission-ready PDF document.

## Features

- **Smart Parsing**: Parses the notebook JSON structure to extract all content
- **Content Extraction**:
  - Markdown cells with proper heading hierarchy
  - Code cells with syntax highlighting
  - Cell outputs (text, tables, images, errors)
- **Professional Formatting**:
  - Custom title page with document info
  - Auto-generated table of contents
  - Styled headers and page numbers
  - Syntax-highlighted code blocks
  - Styled output blocks with distinct backgrounds
  - Error tracebacks in highlighted boxes
- **Clean Output**: Produces a ready-to-submit lab report, not a raw dump

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install reportlab pygments beautifulsoup4 markdown
```

### requirements.txt

```
reportlab>=4.0.0
pygments>=2.14.0
beautifulsoup4>=4.11.0
markdown>=3.4.0
lxml>=4.9.0
```

## Usage

### Basic Usage

```bash
python nb2pdf_agent.py notebook.ipynb
```

This generates `notebook.pdf` in the same directory.

### Specify Output Path

```bash
python nb2pdf_agent.py notebook.ipynb -o report.pdf
```

### Verbose Output

```bash
python nb2pdf_agent.py notebook.ipynb --verbose
```

### Full CLI Help

```bash
python nb2pdf_agent.py --help
```

```
usage: nb2pdf_agent.py [-h] [-o OUTPUT] [-v] input

Convert Jupyter Notebook (.ipynb) to professional PDF

positional arguments:
  input                 Path to the Jupyter Notebook (.ipynb) file

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output PDF path (default: same as input with .pdf extension)
  -v, --verbose         Enable verbose output

Examples:
  python nb2pdf_agent.py notebook.ipynb
  python nb2pdf_agent.py notebook.ipynb -o report.pdf
  python nb2pdf_agent.py path/to/notebook.ipynb --verbose
```

## How It Works

### Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Input .ipynb   │────▶│ NotebookParser   │────▶│  PDFConverter   │
│    File         │     │  (Extract Cells) │     │ (Format & PDF)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │                        │
                                ▼                        ▼
                        ┌──────────────┐        ┌──────────────┐
                        │ - Markdown   │        │ - Title Page │
                        │ - Code       │        │ - TOC        │
                        │ - Outputs    │        │ - Content    │
                        │ - Images     │        │ - Headers    │
                        └──────────────┘        └──────────────┘
```

### Processing Pipeline

1. **Load Notebook**: Reads and parses the JSON structure
2. **Extract Title**: From metadata or first heading
3. **Parse Cells**: Separates markdown, code, and output cells
4. **Convert Markdown**: Transforms markdown to formatted text
5. **Highlight Code**: Applies syntax highlighting to code blocks
6. **Process Outputs**: Handles text, images, and errors
7. **Build PDF**: Assembles all components with professional styling

## Output Structure

The generated PDF includes:

1. **Title Page**
   - Document title (from notebook or first heading)
   - Author/metadata info
   - Clean, centered layout

2. **Table of Contents**
   - Auto-extracted from markdown headings
   - Hierarchical indentation

3. **Content Sections**
   - Formatted markdown text
   - Heading hierarchy (H1, H2, H3)
   - Lists, tables, and inline formatting

4. **Code Blocks**
   - Line numbers
   - Syntax highlighting colors
   - Monospace font

5. **Output Blocks**
   - Light gray background for normal output
   - Red-tinted background for errors
   - Embedded images where applicable

6. **Headers & Footers**
   - Document title in header
   - Page numbers in footer
   - Generation timestamp

## Example

### Sample Input Notebook

```json
{
  "cells": [
    {
      "cell_type": "markdown",
      "source": "# Data Analysis Report\n\nThis notebook presents..."
    },
    {
      "cell_type": "code",
      "source": "import pandas as pd\ndf = pd.read_csv('data.csv')",
      "outputs": [...]
    }
  ],
  "metadata": {"title": "Data Analysis"}
}
```

### Generated Output

The PDF will show:
- "Data Analysis Report" as the main title
- Table of contents with section links
- Formatted introductory text
- Code block with syntax highlighting
- Output displayed in a styled box

## Customization

### Style Modifications

Edit the `COLORS` and `styles` dictionaries in `PDFConverter._create_styles()` to customize:

```python
COLORS = {
    'primary': HexColor('#2c3e50'),    # Main heading color
    'secondary': HexColor('#34495e'),  # Subheading color
    'accent': HexColor('#3498db'),     # Accent/border color
    'code_bg': HexColor('#f8f8f8'),    # Code block background
    'output_bg': HexColor('#f0f0f0'),  # Output background
    'error_bg': HexColor('#ffe6e6'),   # Error background
}
```

### Page Size

Change in `PDFConverter.convert()`:

```python
doc = SimpleDocTemplate(
    ...,
    pagesize=A4,  # or letter, legal, etc.
    ...
)
```

## Troubleshooting

### Issue: Images not rendering

**Solution**: Ensure PIL/Pillow is installed and image data is properly base64-encoded in the notebook.

### Issue: Markdown not formatting

**Solution**: Check that `markdown` and `beautifulsoup4` packages are installed.

### Issue: Syntax highlighting not working

**Solution**: Verify `pygments` is installed: `pip install pygments`

### Issue: Large notebooks causing memory issues

**Solution**: For very large notebooks, consider processing in batches or increasing output limits in `_create_output_block()`.

## File Structure

```
jupyter-to-pdf-converter-agent/
├── nb2pdf_agent.py      # Main agent script
├── README.md            # This documentation
├── requirements.txt     # Python dependencies
├── sample_notebook.ipynb  # Example notebook
└── sample_output.pdf    # Demo output
```

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions welcome! Please feel free to submit issues and pull requests.

## Support

For issues and questions, please open a GitHub issue.
