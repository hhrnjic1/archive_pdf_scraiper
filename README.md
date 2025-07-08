# POF Journal Scraper

A Python scraper for downloading and processing articles from Prilozi za orijentalnu filologiju (POF) journal. The scraper automatically detects article language and processes only Bosnian/Croatian/Serbian articles, converting Cyrillic to Latin script where necessary.

## Project Overview

The POF Journal Scraper is a comprehensive web scraping solution designed to extract academic articles from the Prilozi za orijentalnu filologiju (POF) journal archive. The system intelligently filters articles by language (Bosnian/Croatian/Serbian), downloads PDFs, extracts text content, and formats it into a structured dataset suitable for research and analysis.

## Features

- Automatic language detection and filtering
- PDF download with multiple fallback methods
- Text extraction with OCR support for scanned documents
- Cyrillic to Latin script conversion
- Progress tracking and resume capability
- Automatic retry mechanism with exponential backoff
- Configurable save intervals
- Robust error handling and logging

## Prerequisites

- Python 3.8+
- Chrome/Chromium browser
- Tesseract OCR (for scanned PDFs)

### Installing Tesseract OCR

**macOS:**
```bash
brew install tesseract
brew install tesseract-lang  # For additional language support
```

**Windows:**
1. Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
2. Install and add to system PATH

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pof-journal-scraper.git
cd pof-journal-scraper
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the scraper:
```bash
python main.py
```

The script will:
1. Check all required dependencies
2. Start scraping all issues and articles
3. Save progress periodically (every 10 articles by default)
4. Create `scraped_articles` folder with:
   - `pdfs/` - downloaded PDF files
   - `all_articles.txt` - processed text from all articles

### Configuration Options

You can modify the scraper parameters in `main.py`:

```python
output_file = run_local_scraper(
    limit_issues=None,    # Set to number to limit issues scraped
    limit_articles=None,  # Set to number to limit articles per issue
    save_interval=10,     # Save progress after N articles
    resume_from=None      # URL to resume from if interrupted
)
```

### Resuming Interrupted Scraping

The scraper automatically saves progress. If interrupted, it will resume from the last saved state when run again.

## Output Format

Articles are saved in the following format:

```
<***>
NOVINA: Prilozi za orijentalnu filologiju
DATUM: 2023
RUBRIKA: History
NADNASLOV: N/A
NASLOV: Article Title
PODNASLOV: N/A
STRANA: 123-145
AUTOR(I): John Doe; Jane Smith
[Article text content...]
```

## Language Support

The scraper processes articles in:
- Bosnian (bs)
- Croatian (hr)
- Serbian (sr)

Articles in other languages (especially English and Turkish) are automatically filtered out.

## Troubleshooting

### Common Issues

1. **Chrome WebDriver Issues**
   - Ensure Chrome/Chromium is installed
   - WebDriver manager will automatically download the correct driver

2. **PDF Extraction Issues**
   - Some PDFs may be scanned documents
   - Ensure Tesseract OCR is properly installed
   - Check that tesseract-lang package is installed for better accuracy

3. **Language Detection Issues**
   - The scraper uses multiple methods to detect language
   - Articles with mixed languages may sometimes be incorrectly filtered

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Results & Performance

### Scraping Statistics
- **Total Articles Processed**: 349 articles
- **PDFs Downloaded**: 393 files
- **Total Dataset Size**: 395 MB
- **Text Content**: 27,395 lines of processed text
- **Languages Processed**: Bosnian, Croatian, Serbian (including Cyrillic to Latin conversion)

### Performance Metrics
- **Success Rate**: ~89% (349 articles successfully processed from 393 PDFs)
- **Language Detection Accuracy**: High accuracy with multi-stage filtering
- **Download Speed**: Approximately 10 articles per minute (with delays to respect server resources)
- **Text Extraction**: Successful extraction from both searchable and scanned PDFs using OCR

### Data Quality
- Structured metadata for each article including:
  - Title, Authors, Publication year
  - Page numbers, Journal section
  - Full text content with headers and references removed
- Consistent formatting across all articles
- Cyrillic content automatically converted to Latin script

## Algorithm & Program Flow

### Core Algorithm
1. **Archive Discovery**: Scrape journal archive pages to identify all issues
2. **Issue Processing**: For each issue, extract article metadata and PDF links
3. **Language Pre-filtering**: Quick language detection on article titles
4. **PDF Download**: Multi-method download approach (direct HTTP, Selenium fallback)
5. **Text Extraction**: PyPDF2 for searchable PDFs, OCR for scanned documents
6. **Language Validation**: Comprehensive language detection on full text
7. **Text Processing**: Clean and format text according to specifications
8. **Data Storage**: Structured output with metadata headers

### Processing Pipeline
```
Archive Pages → Issues → Articles → Language Filter → PDF Download → Text Extraction → Language Validation → Text Processing → Structured Output
```

### Key Components
- **POFJournalLocalScraper**: Main scraper class handling all operations
- **Language Detection**: Multi-stage filtering using langdetect and keyword analysis
- **PDF Processing**: Dual-mode extraction (standard + OCR)
- **Progress Management**: Automatic saving and resume capability
- **Error Handling**: Robust retry mechanisms with exponential backoff

## Demo Version

To run a demo with limited scope:

```python
# Demo configuration - processes only first 2 issues with 5 articles each
output_file = run_local_scraper(
    limit_issues=2,        # Process only first 2 issues
    limit_articles=5,      # Process only first 5 articles per issue
    save_interval=5        # Save progress every 5 articles
)
```

This demo version will:
- Process approximately 10 articles
- Complete in under 5 minutes
- Demonstrate all core functionality
- Generate sample output files

## Acknowledgments

- POF Journal for providing access to their archive
- All the open-source libraries used in this project