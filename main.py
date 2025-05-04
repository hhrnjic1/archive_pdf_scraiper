# -*- coding: utf-8 -*-
"""
# POF Journal Scraper - Local Version
This script scrapes articles from POF journal, downloads PDFs, and extracts text.
"""

import sys
import subprocess
import os
import platform

# Function to check and install required packages
def check_and_install_packages():
    """Check if required packages are installed and provide installation instructions"""
    required_packages = {
        'requests': '2.28.0',
        'beautifulsoup4': '4.11.0',
        'tqdm': '4.65.0',
        'cyrtranslit': '1.0',
        'PyPDF2': '3.0.0',
        'selenium': '4.8.0',
        'webdriver-manager': '3.8.5',
        'pytesseract': '0.3.10',
        'pdf2image': '1.16.3',
        'langdetect': '1.0.9',
        'Pillow': '10.0.0'  # Changed to compatible version
    }
    
    missing_packages = []
    installed_packages = []
    
    print("Checking required packages...")
    print("-" * 50)
    
    for package, version in required_packages.items():
        try:
            __import__(package.replace('-', '_'))
            installed_packages.append(package)
            print(f"✓ {package} is installed")
        except ImportError:
            missing_packages.append(f"{package}")  # Removed version specification
            print(f"✗ {package} is NOT installed")
    
    print("-" * 50)
    
    if missing_packages:
        print("\nTo install missing packages, run:")
        print(f"pip install {' '.join(missing_packages)}")
        print("\nOr install one by one:")
        for package in missing_packages:
            print(f"pip install {package}")
        
        print("\nDo you want to install missing packages automatically? (y/n)")
        response = input().lower().strip()
        
        if response == 'y':
            for package in missing_packages:
                try:
                    print(f"\nInstalling {package}...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                    print(f"✓ {package} installed successfully")
                except subprocess.CalledProcessError:
                    print(f"✗ Failed to install {package}")
                    print(f"Please install manually: pip install {package}")
        else:
            print("\nPlease install the missing packages manually before running the scraper.")
            sys.exit(1)
    else:
        print("\nAll required packages are installed!")
    
    # Check for additional system requirements
    print("\nChecking system requirements...")
    
    # Check for Tesseract OCR
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        print("✓ Tesseract OCR is installed")
    except:
        print("✗ Tesseract OCR is NOT installed")
        print("\nTo install Tesseract OCR:")
        if platform.system() == "Windows":
            print("1. Download from: https://github.com/UB-Mannheim/tesseract/wiki")
            print("2. Install it (remember the installation path)")
            print("3. Add Tesseract to your system PATH")
            print("   OR set the path in your code: pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'")
        elif platform.system() == "Darwin":  # macOS
            print("Run: brew install tesseract")
        else:  # Linux
            print("Run: sudo apt-get install tesseract-ocr")
    
    # Check for Chrome/Chromium
    print("\nFor Selenium, you'll need Chrome or Chromium browser installed.")
    print("The script will automatically download the appropriate ChromeDriver using webdriver-manager.")
    
    print("\nSetup check completed!")
    print("=" * 50)

# Run the check first
check_and_install_packages()

# Now import all required modules
import re
import requests
import time
import shutil
import base64
from bs4 import BeautifulSoup
import logging
from tqdm import tqdm
import random
import PyPDF2
import io
from pathlib import Path
import json

# Language detection imports
from langdetect import detect, detect_langs, DetectorFactory
DetectorFactory.seed = 0  # For consistent results

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Try to import Cyrillic to Latin conversion
try:
    import cyrtranslit
    cyrillic_converter = True
    print("Cyrillic to Latin conversion is available.")
except ImportError:
    cyrillic_converter = False
    print("cyrtranslit not found. Some features may be limited.")

# Try to import OCR libraries
try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_path
    
    # For Windows users, set Tesseract path if not in PATH
    if platform.system() == "Windows":
        # Adjust this path if Tesseract is installed elsewhere
        tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    ocr_available = True
    print("OCR libraries available.")
except ImportError:
    ocr_available = False
    print("OCR libraries not available. Some scanned PDFs may not be processed correctly.")

class POFJournalLocalScraper:
    def __init__(self, output_dir='scraped_articles'):
        """
        Initialize the journal scraper for local use.

        Args:
            output_dir: Directory to save processed text files
        """
        self.base_url = "https://pof.ois.unsa.ba"
        self.output_dir = output_dir
        self.pdf_dir = os.path.join(output_dir, 'pdfs')

        # Create output directories if they don't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        if not os.path.exists(self.pdf_dir):
            os.makedirs(self.pdf_dir)

        # Session for making HTTP requests with different headers
        self.session = requests.Session()
        self.update_session_headers()

        # Initialize Selenium browser
        self.driver = None
        
        # Progress tracking parameters
        self.save_interval = 10  # Save progress after every N articles
        self.resume_from = None  # URL to resume scraping from
        self.progress_file = os.path.join(output_dir, 'scraping_progress.json')

    def update_session_headers(self):
        """Update session headers to mimic different browsers"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
        ]

        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }

        self.session.headers.update(headers)

    def setup_chrome_driver(self):
        """Set up Chrome WebDriver for local environment"""
        try:
            print("Setting up Chrome WebDriver...")

            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in headless mode
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')

            # Set download preferences
            prefs = {
                "download.default_directory": self.pdf_dir,
                "download.prompt_for_download": False,
                "plugins.always_open_pdf_externally": True
            }
            chrome_options.add_experimental_option("prefs", prefs)

            # Use webdriver-manager to automatically manage chromedriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            print("Chrome WebDriver initialized successfully.")
            return True

        except Exception as e:
            print(f"Error setting up Chrome WebDriver: {e}")
            print("Make sure Chrome/Chromium is installed on your system.")
            return False

    def close_chrome_driver(self):
        """Close Chrome WebDriver if it's running"""
        if self.driver:
            try:
                self.driver.quit()
                print("Chrome WebDriver closed.")
            except:
                pass
            self.driver = None

    def get_issue_links(self):
        """
        Get list of issue links from the archive.

        Returns:
            List of issue URLs
        """
        issue_links = []

        # Fetch all issues from the archive page (multiple pages)
        archive_urls = [
            "https://pof.ois.unsa.ba/index.php/pof/issue/archive",
            "https://pof.ois.unsa.ba/index.php/pof/issue/archive/1",
            "https://pof.ois.unsa.ba/index.php/pof/issue/archive/2",
            "https://pof.ois.unsa.ba/index.php/pof/issue/archive/3"
        ]

        try:
            for archive_url in archive_urls:
                print(f"Fetching issues from archive page: {archive_url}")
                self.update_session_headers()  # Change headers for each request
                response = self.session.get(archive_url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                # Find all issue links based on the HTML structure
                for link in soup.select('a.cover'):
                    issue_url = link.get('href')
                    if issue_url and issue_url not in issue_links:
                        print(f"Found issue: {issue_url}")
                        issue_links.append(issue_url)

                # Brief pause to avoid overwhelming the server
                time.sleep(1)
        except Exception as e:
            print(f"Error fetching issues from archive: {e}")

        print(f"Total issues found: {len(issue_links)}")
        return issue_links

    def get_article_links_from_issue(self, issue_url):
        """
        Extract links to all articles from an issue page.

        Args:
            issue_url: URL of the issue

        Returns:
            List of article data dictionaries
        """
        article_data = []

        try:
            print(f"Fetching articles from issue: {issue_url}")
            self.update_session_headers()
            response = self.session.get(issue_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Get issue title/number for metadata
            issue_title = soup.select_one('h1')
            issue_info = issue_title.text.strip() if issue_title else "Unknown Issue"
            print(f"Processing issue: {issue_info}")

            # Extract year from issue info
            issue_year = ""
            year_match = re.search(r'\((19|20)\d{2}\)', issue_info)
            if year_match:
                issue_year = year_match.group(0).strip('()')
                print(f"Extracted year: {issue_year}")

            # Find all article sections
            sections = soup.select('.sections .section')

            for section in sections:
                # Get section name (if available)
                section_name = "N/A"
                section_heading = section.select_one('h2')
                if section_heading:
                    section_name = section_heading.text.strip()

                # Find all article summaries in this section
                article_summaries = section.select('.obj_article_summary')
                print(f"Found {len(article_summaries)} articles in section '{section_name}'")

                for summary in article_summaries:
                    article_data_item = {
                        'issue_info': issue_info,
                        'rubrika': section_name,
                        'year': issue_year
                    }

                    # Extract article URL and title
                    title_link = summary.select_one('.title a')
                    if title_link:
                        article_url = title_link.get('href')
                        article_data_item['article_url'] = article_url
                        article_data_item['title'] = title_link.text.strip()
                        print(f"Found article: {article_data_item['title']}")

                        # Extract article ID from the URL
                        id_match = re.search(r'/view/(\d+)', article_url)
                        if id_match:
                            article_data_item['article_id'] = id_match.group(1)

                    # Extract metadata
                    meta = summary.select_one('.meta')
                    if meta:
                        # Authors
                        authors_elem = meta.select_one('.authors')
                        if authors_elem:
                            article_data_item['authors'] = authors_elem.text.strip()

                        # Pages
                        pages_elem = meta.select_one('.pages')
                        if pages_elem:
                            article_data_item['pages'] = pages_elem.text.strip()

                    # Direct PDF link
                    pdf_link = summary.select_one('.obj_galley_link.pdf')
                    if pdf_link:
                        pdf_url = pdf_link.get('href')
                        article_data_item['pdf_url'] = pdf_url
                        print(f"Found direct PDF link: {pdf_url}")

                    # Only add if we have at least URL or PDF URL
                    if 'article_url' in article_data_item or 'pdf_url' in article_data_item:
                        article_data.append(article_data_item)

            # If no articles found with the section approach, try direct selection
            if not article_data:
                print("No articles found with section-based approach, trying direct selection...")
                article_summaries = soup.select('.obj_article_summary')
                print(f"Found {len(article_summaries)} articles directly")

                for summary in article_summaries:
                    # Process each article summary similar to above
                    article_data_item = {'issue_info': issue_info, 'rubrika': 'N/A', 'year': issue_year}

                    title_link = summary.select_one('.title a')
                    if title_link:
                        article_data_item['article_url'] = title_link.get('href')
                        article_data_item['title'] = title_link.text.strip()

                        # Extract article ID
                        article_url = article_data_item['article_url']
                        id_match = re.search(r'/view/(\d+)', article_url)
                        if id_match:
                            article_data_item['article_id'] = id_match.group(1)

                    # Extract metadata
                    meta = summary.select_one('.meta')
                    if meta:
                        # Authors
                        authors_elem = meta.select_one('.authors')
                        if authors_elem:
                            article_data_item['authors'] = authors_elem.text.strip()

                        # Pages
                        pages_elem = meta.select_one('.pages')
                        if pages_elem:
                            article_data_item['pages'] = pages_elem.text.strip()

                    # Direct PDF link
                    pdf_link = summary.select_one('.obj_galley_link.pdf')
                    if pdf_link:
                        article_data_item['pdf_url'] = pdf_link.get('href')

                    # Only add if we have at least URL or PDF URL
                    if 'article_url' in article_data_item or 'pdf_url' in article_data_item:
                        article_data.append(article_data_item)

        except Exception as e:
            print(f"Error getting article links from issue {issue_url}: {e}")
            logger.error(f"Error getting article links from issue {issue_url}: {e}")

        return article_data

    def get_article_details(self, article_data):
        """
        Get additional details from article page if needed.

        Args:
            article_data: Basic data about the article

        Returns:
            Updated article data with more details
        """
        # If we already have title, authors, and pages, we can skip this
        if 'title' in article_data and 'authors' in article_data and 'pages' in article_data:
            return article_data

        article_url = article_data.get('article_url')
        if not article_url:
            return article_data

        try:
            print(f"Fetching additional details from article page: {article_url}")
            self.update_session_headers()
            response = self.session.get(article_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find PDF link if not already available
            if 'pdf_url' not in article_data:
                pdf_link = soup.select_one('.obj_galley_link.pdf')
                if pdf_link:
                    pdf_url = pdf_link.get('href')
                    article_data['pdf_url'] = pdf_url
                    print(f"Found PDF link from article page: {pdf_url}")

            # Get additional metadata if not already present
            if 'title' not in article_data:
                title_elem = soup.select_one('h1.page_title')
                if title_elem:
                    article_data['title'] = title_elem.text.strip()

            if 'authors' not in article_data:
                authors_elem = soup.select('.authors .name')
                if authors_elem:
                    authors = [author.text.strip() for author in authors_elem]
                    article_data['authors'] = '; '.join(authors)

            if 'pages' not in article_data:
                pages_elem = soup.select_one('.pages .value')
                if pages_elem:
                    article_data['pages'] = pages_elem.text.strip()

            # Publication date
            if 'year' not in article_data:
                date_elem = soup.select_one('.published .value')
                if date_elem:
                    article_data['date'] = date_elem.text.strip()
                    # Extract year
                    year_match = re.search(r'\b(19|20)\d{2}\b', article_data['date'])
                    if year_match:
                        article_data['year'] = year_match.group(0)

        except Exception as e:
            print(f"Error getting details from article page {article_url}: {e}")
            logger.error(f"Error getting details from article page {article_url}: {e}")

        return article_data

    def download_pdf_using_requests(self, pdf_url, article_id):
        """
        Download PDF using direct requests without browser automation.

        Args:
            pdf_url: URL of the PDF
            article_id: ID of the article for filename

        Returns:
            Path to downloaded PDF file or None if failed
        """
        try:
            print(f"Downloading PDF from {pdf_url} using direct request...")

            # First check if we already have this PDF
            pdf_path = os.path.join(self.pdf_dir, f"article_{article_id}.pdf")
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
                print(f"PDF already exists at {pdf_path}, skipping download")
                return pdf_path

            # Make request with custom headers
            self.update_session_headers()
            headers = self.session.headers
            headers.update({
                'Accept': 'application/pdf,application/x-pdf',
                'Referer': self.base_url
            })

            # First, get the page that contains the actual PDF link
            response = self.session.get(pdf_url, headers=headers)
            response.raise_for_status()

            # Parse the HTML to find the actual PDF download link
            soup = BeautifulSoup(response.text, 'html.parser')
            iframe = soup.select_one('iframe#pdf')
            direct_pdf_link = None

            if iframe and 'src' in iframe.attrs:
                direct_pdf_link = iframe.get('src')
                print(f"Found PDF in iframe: {direct_pdf_link}")
            else:
                # Try finding direct download links
                download_links = soup.select('a.download')
                for link in download_links:
                    if link.get('href') and '.pdf' in link.get('href').lower():
                        direct_pdf_link = link.get('href')
                        print(f"Found direct PDF download link: {direct_pdf_link}")
                        break

            if not direct_pdf_link:
                print("Could not find direct PDF link through any method")
                return None

            # If link is relative, make it absolute
            if direct_pdf_link.startswith('/'):
                direct_pdf_link = f"{self.base_url}{direct_pdf_link}"
            elif not direct_pdf_link.startswith('http'):
                base_path = '/'.join(pdf_url.split('/')[:-1])
                direct_pdf_link = f"{base_path}/{direct_pdf_link}"

            # Now download the actual PDF
            print(f"Attempting to download actual PDF from: {direct_pdf_link}")

            # Add retry mechanism
            max_retries = 5
            retry_delay = 2  # Initial delay in seconds

            for retry in range(max_retries):
                try:
                    pdf_response = self.session.get(direct_pdf_link, headers=headers, stream=True, timeout=30)
                    pdf_response.raise_for_status()
                    break
                except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                    if retry < max_retries - 1:
                        wait_time = retry_delay * (2 ** retry)  # Exponential backoff
                        print(f"Request failed: {e}. Retrying in {wait_time} seconds (attempt {retry+1}/{max_retries})")
                        time.sleep(wait_time)
                        self.update_session_headers()
                        headers = self.session.headers
                    else:
                        print(f"All retry attempts failed: {e}")
                        raise

            # Save to file
            with open(pdf_path, 'wb') as f:
                for chunk in pdf_response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"PDF downloaded and saved to {pdf_path}")

            # Verify the file is a valid PDF
            if os.path.getsize(pdf_path) < 1000:
                print("Warning: Downloaded file is very small, might not be a valid PDF")
                with open(pdf_path, 'rb') as f:
                    header = f.read(5)
                    if header != b'%PDF-':
                        print("Downloaded file is not a valid PDF")
                        return None

            return pdf_path

        except Exception as e:
            print(f"Error downloading PDF using direct request: {e}")
            return None

    def download_pdf_using_selenium(self, pdf_url, article_id):
        """
        Download PDF using Selenium browser automation.

        Args:
            pdf_url: URL of the PDF
            article_id: ID of the article for filename

        Returns:
            Path to downloaded PDF file or None if failed
        """
        if not self.driver:
            if not self.setup_chrome_driver():
                print("Failed to set up Chrome WebDriver")
                return None

        try:
            print(f"Trying to download PDF using Selenium: {pdf_url}")

            # Navigate to the PDF page
            self.driver.get(pdf_url)
            time.sleep(5)  # Wait for page to load

            # Try to find PDF iframe or download link
            try:
                # First check for an iframe
                try:
                    iframe = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#pdf"))
                    )

                    # Get the iframe source
                    iframe_src = iframe.get_attribute('src')
                    print(f"Found iframe with source: {iframe_src}")

                    # Download using requests
                    self.update_session_headers()
                    headers = self.session.headers
                    headers.update({
                        'Accept': 'application/pdf,application/x-pdf',
                        'Referer': pdf_url
                    })

                    r = self.session.get(iframe_src, headers=headers, stream=True)
                    r.raise_for_status()

                    pdf_path = os.path.join(self.pdf_dir, f"article_{article_id}.pdf")
                    with open(pdf_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)

                    print(f"PDF downloaded via iframe source to {pdf_path}")
                    return pdf_path

                except (TimeoutException, NoSuchElementException):
                    print("No iframe found, looking for download links...")

                # Look for download links/buttons
                try:
                    download_elements = self.driver.find_elements(By.CSS_SELECTOR, ".download")
                    if download_elements:
                        for elem in download_elements:
                            if elem.is_displayed():
                                print("Found download element, clicking...")
                                elem.click()
                                time.sleep(5)  # Wait for download

                                # For now, let's assume we can use the download URL
                                if elem.tag_name == 'a':
                                    download_url = elem.get_attribute('href')
                                    if download_url:
                                        self.update_session_headers()
                                        r = self.session.get(download_url, stream=True)
                                        r.raise_for_status()

                                        pdf_path = os.path.join(self.pdf_dir, f"article_{article_id}.pdf")
                                        with open(pdf_path, 'wb') as f:
                                            for chunk in r.iter_content(chunk_size=8192):
                                                f.write(chunk)

                                        print(f"PDF downloaded via download link to {pdf_path}")
                                        return pdf_path

                except Exception as e:
                    print(f"Error looking for download links: {e}")

            except Exception as e:
                print(f"Error in Selenium PDF download: {e}")

            # If all methods fail, return None
            print("All Selenium methods failed to download PDF")
            return None

        except Exception as e:
            print(f"Error in Selenium PDF download: {e}")
            return None
        finally:
            # Reset frame focus
            if self.driver:
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass

    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text
        """
        if not pdf_path or not os.path.exists(pdf_path):
            print(f"PDF file not found at {pdf_path}")
            return ""

        text = ""

        try:
            print(f"Extracting text from PDF: {pdf_path}")

            # Try PyPDF2 first
            try:
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    num_pages = len(reader.pages)
                    print(f"PDF has {num_pages} pages")

                    for page_num in range(num_pages):
                        try:
                            page = reader.pages[page_num]
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                            print(f"Extracted page {page_num+1}/{num_pages}")
                        except Exception as page_e:
                            print(f"Error extracting text from page {page_num+1}: {page_e}")
            except Exception as e:
                print(f"Error using PyPDF2: {e}")

            # If standard extraction methods fail, try OCR if available
            if not text.strip() and ocr_available:
                print("Standard extraction methods failed. Trying OCR...")
                try:
                    # Convert PDF to images
                    images = convert_from_path(pdf_path)

                    # Extract text from each image
                    ocr_text = ""
                    for i, image in enumerate(images):
                        print(f"Processing page {i+1}/{len(images)} with OCR...")
                        page_text = pytesseract.image_to_string(image)
                        ocr_text += page_text + "\n\n"

                    if ocr_text.strip():
                        print("Successfully extracted text using OCR!")
                        text = ocr_text
                    else:
                        print("OCR extraction produced no text")
                except Exception as e:
                    print(f"Error during OCR extraction: {e}")

        except Exception as e:
            print(f"Error extracting text from PDF: {e}")

        if not text:
            print("WARNING: No text extracted from PDF. This might be a scanned document.")

        return text

    def _contains_cyrillic(self, text):
        """
        Check if text contains Cyrillic characters.

        Args:
            text: Text to check

        Returns:
            Boolean indicating if text contains Cyrillic
        """
        if not text:
            return False

        cyrillic_pattern = re.compile(r'[А-Яа-я]')
        has_cyrillic = bool(cyrillic_pattern.search(text))
        if has_cyrillic:
            print("Detected Cyrillic characters in the text")
        return has_cyrillic

    def _convert_cyrillic_to_latin(self, text):
        """
        Convert Cyrillic text to Latin.

        Args:
            text: Cyrillic text

        Returns:
            Latin text
        """
        if not text:
            return text

        if not cyrillic_converter:
            logger.warning("Cyrillic to Latin conversion is disabled because cyrtranslit is not installed")
            return text

        try:
            print("Converting Cyrillic to Latin script...")
            return cyrtranslit.to_latin(text)
        except Exception as e:
            print(f"Error converting Cyrillic to Latin: {e}")
            logger.error(f"Error converting Cyrillic to Latin: {e}")
            return text

    def _clean_text(self, text):
        """
        Clean the text according to requirements.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        print("Starting text cleaning process...")
        original_length = len(text)

        # 1. Remove headers, footers, and page numbers
        print("Removing headers, footers, and page numbers...")
        text = re.sub(r'_{10,}', '', text)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^.*UDK.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^.*DOI:.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'Ključne riječi:.*$', '', text, flags=re.MULTILINE)

        # 2. Remove literature sections
        print("Removing literature sections...")
        text = re.sub(r'Literatura\s*\n.*?(?=<\*\*\*>|$)', '', text, flags=re.DOTALL)
        text = re.sub(r'References\s*\n.*?(?=<\*\*\*>|$)', '', text, flags=re.DOTALL)
        text = re.sub(r'Bibliography\s*\n.*?(?=<\*\*\*>|$)', '', text, flags=re.DOTALL)

        # 3. Remove numbered headings and subheadings
        print("Removing headings and subheadings...")
        text = re.sub(r'^\s*\d+(\.\d+)*\s+.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*[IVX]+\.\s+.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*(UVOD|ZAKLJUČAK)\s*$', '', text, flags=re.MULTILINE)

        # 4. Remove references
        print("Removing references...")
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\([A-Za-z]+\s*,?\s*\d{4}(:\s*\d+)?\)', '', text)
        text = re.sub(r'\([A-Za-z]+ et al\.,\s*\d{4}\)', '', text)
        text = re.sub(r'\([A-Za-z]+ & [A-Za-z]+,\s*\d{4}\)', '', text)

        # 5. Remove parts in foreign languages
        print("Removing foreign language sections...")
        text = re.sub(r'Summary\s*\n.*?(?=<\*\*\*>|$)', '', text, flags=re.DOTALL)
        text = re.sub(r'Abstract\s*\n.*?(?=<\*\*\*>|$)', '', text, flags=re.DOTALL)

        # 6. Remove unknown characters
        print("Handling unknown characters...")
        text = re.sub(r'[^\x00-\x7F]', ' ', text)

        # 7. Remove newlines within paragraphs
        print("Fixing paragraph formatting...")
        paragraphs = text.split('\n\n')
        processed_paragraphs = []

        for paragraph in paragraphs:
            processed_paragraph = ' '.join(paragraph.split('\n'))
            processed_paragraphs.append(processed_paragraph)

        # Rejoin paragraphs with double newlines
        processed_text = '\n\n'.join(processed_paragraphs)

        new_length = len(processed_text)
        print(f"Cleaned text: removed {original_length - new_length} characters")

        return processed_text

    def _process_extracted_text(self, text, metadata):
        """
        Process the extracted text according to requirements.

        Args:
            text: Raw extracted text
            metadata: Dictionary of article metadata

        Returns:
            Processed text
        """
        # If there's no text, just return the metadata structure
        if not text:
            formatted_text = "<***>\n"
            formatted_text += f"NOVINA: {metadata['NOVINA']}\n"
            formatted_text += f"DATUM: {metadata['DATUM']}\n"
            formatted_text += f"RUBRIKA: {metadata['RUBRIKA']}\n"
            formatted_text += f"NADNASLOV: {metadata['NADNASLOV']}\n"
            formatted_text += f"NASLOV: {metadata['NASLOV']}\n"
            formatted_text += f"PODNASLOV: {metadata['PODNASLOV']}\n"
            formatted_text += f"STRANA: {metadata['STRANA']}\n"
            formatted_text += f"AUTOR(I): {metadata['AUTOR(I)']}\n"
            formatted_text += "\n\n"  # Add blank line at the end
            return formatted_text

        # Convert Cyrillic to Latin if needed
        if self._contains_cyrillic(text):
            text = self._convert_cyrillic_to_latin(text)

        # Clean the text
        cleaned_text = self._clean_text(text)

        # Format according to requirements
        formatted_text = "<***>\n"
        formatted_text += f"NOVINA: {metadata['NOVINA']}\n"
        formatted_text += f"DATUM: {metadata['DATUM']}\n"
        formatted_text += f"RUBRIKA: {metadata['RUBRIKA']}\n"
        formatted_text += f"NADNASLOV: {metadata['NADNASLOV']}\n"
        formatted_text += f"NASLOV: {metadata['NASLOV']}\n"
        formatted_text += f"PODNASLOV: {metadata['PODNASLOV']}\n"
        formatted_text += f"STRANA: {metadata['STRANA']}\n"
        formatted_text += f"AUTOR(I): {metadata['AUTOR(I)']}\n"
        formatted_text += cleaned_text
        formatted_text += "\n\n"  # Add blank line at the end

        return formatted_text

    def should_process_article(self, article_data):
        """
        Quick check if article should be processed based on title language.
        
        Args:
            article_data: Basic article data
            
        Returns:
            Boolean indicating if article should be processed
        """
        title = article_data.get('title', '')
        if not title:
            return True  # Process if no title
        
        try:
            # Quick language detection on title
            detected_lang = detect(title)
            print(f"Title language detected: {detected_lang} for '{title}'")
            
            # If title is in English or Turkish, skip
            if detected_lang in ['en', 'tr']:
                return False
                
            # If title contains certain keywords that indicate it's not in desired language
            english_keywords = ['introduction', 'abstract', 'summary', 'review', 'analysis', 'studies', 'research']
            turkish_keywords = ['özet', 'giriş', 'sonuç', 'analiz', 'araştırma', 'çalışma']
            
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in english_keywords + turkish_keywords):
                return False
                
        except Exception as e:
            print(f"Error in title language detection: {e}")
            
        return True

    def process_article(self, article_data):
        """
        Process a single article: download PDF, extract text, and format.
        Only processes articles in desired languages.
        
        Args:
            article_data: Data about the article
            
        Returns:
            Formatted article text or None if language doesn't match
        """
        # Quick check on title before downloading
        if not self.should_process_article(article_data):
            print(f"Skipping article based on title: {article_data.get('title', 'Unknown')}")
            return None
        
        # Get additional article details if needed
        article_data = self.get_article_details(article_data)
        
        # Check if we have a PDF URL
        pdf_url = article_data.get('pdf_url')
        if not pdf_url:
            print(f"No PDF URL found for article: {article_data.get('title')}")
            return None
        
        # Try to download PDF directly using requests
        article_id = article_data.get('article_id', f"unknown_{random.randint(1000, 9999)}")
        pdf_path = self.download_pdf_using_requests(pdf_url, article_id)
        
        # If direct download fails, try Selenium
        if not pdf_path:
            print(f"Direct download failed, trying Selenium for article: {article_data.get('title')}")
            pdf_path = self.download_pdf_using_selenium(pdf_url, article_id)
        
        if not pdf_path:
            print(f"All download methods failed for article: {article_data.get('title')}")
            return None
        
        # Extract text from PDF
        text = self.extract_text_from_pdf(pdf_path)
        
        # Language detection - first try to detect from content
        if text and len(text.strip()) > 50:  # Need enough text for reliable detection
            try:
                # Get language probabilities
                detected_langs = detect_langs(text[:1000])  # Use first 1000 chars for detection
                print(f"Detected languages for '{article_data.get('title', 'Unknown')}': {detected_langs}")
                
                # Check if article is in desired languages (bs/hr/sr)
                is_desired_language = False
                for lang_prob in detected_langs:
                    if lang_prob.lang in ['bs', 'hr', 'sr'] and lang_prob.prob > 0.7:
                        is_desired_language = True
                        break
                
                # If not in desired language but has high probability of being in Bosnian/Croatian/Serbian
                if not is_desired_language:
                    for lang_prob in detected_langs:
                        if lang_prob.lang in ['sl', 'mk'] and lang_prob.prob > 0.8:
                            # Check for specific words that indicate B/C/S
                            bcs_indicators = ['je', 'u', 'i', 'na', 'da', 'se', 'za', 'od', 'koji', 'koja', 'što', 'čak', 'već', 'ali', 'kao']
                            text_lower = text[:500].lower()
                            indicator_count = sum(1 for word in bcs_indicators if word in text_lower)
                            if indicator_count > 5:
                                is_desired_language = True
                                print(f"Detected as similar Slavic language, but likely B/C/S based on indicators")
                                break
                
                # Additional check: if it contains Cyrillic, it's likely Serbian
                if not is_desired_language and self._contains_cyrillic(text):
                    is_desired_language = True
                    print(f"Contains Cyrillic script, assuming Serbian")
                
                if not is_desired_language:
                    print(f"Skipping article '{article_data.get('title', 'Unknown')}' - not in desired language")
                    return None
                    
            except Exception as e:
                print(f"Error detecting language: {e}")
                # If detection fails, include the article but mark it
                print(f"Language detection failed, including article by default")
        
        # Create metadata dictionary
        metadata = {
            'NOVINA': 'Prilozi za orijentalnu filologiju',
            'DATUM': article_data.get('year', ''),
            'RUBRIKA': article_data.get('rubrika', 'N/A'),
            'NADNASLOV': 'N/A',
            'NASLOV': article_data.get('title', 'Unknown Title'),
            'PODNASLOV': 'N/A',
            'STRANA': article_data.get('pages', ''),
            'AUTOR(I)': article_data.get('authors', '')
        }
        
        # Process the text
        return self._process_extracted_text(text, metadata)

    def save_progress(self, issue_url, processed_issues, all_articles_text):
        """
        Save scraping progress to a file for potential resumption.

        Args:
            issue_url: Current issue URL being processed
            processed_issues: List of already processed issue URLs
            all_articles_text: Current accumulated article text
        """
        progress_data = {
            'current_issue': issue_url,
            'processed_issues': processed_issues,
            'last_update': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        # Save progress data
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2)

        # Save current articles text
        temp_output_file = os.path.join(self.output_dir, 'all_articles_partial.txt')
        with open(temp_output_file, 'w', encoding='utf-8') as f:
            f.write(all_articles_text)

        print(f"Progress saved. Processed {len(processed_issues)} issues.")

    def load_progress(self):
        """
        Load previously saved scraping progress.

        Returns:
            Tuple of (current_issue, processed_issues, all_articles_text)
        """
        if not os.path.exists(self.progress_file):
            return None, [], ""

        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)

            # Load current articles text
            temp_output_file = os.path.join(self.output_dir, 'all_articles_partial.txt')
            all_articles_text = ""
            if os.path.exists(temp_output_file):
                with open(temp_output_file, 'r', encoding='utf-8') as f:
                    all_articles_text = f.read()

            return progress_data.get('current_issue'), progress_data.get('processed_issues', []), all_articles_text

        except Exception as e:
            print(f"Error loading progress: {e}")
            return None, [], ""

    def scrape_and_process(self, limit_issues=None, limit_articles=None):
        """
        Scrape articles, download PDFs, extract text, and format.

        Args:
            limit_issues: Optional limit on number of issues to process
            limit_articles: Optional limit on number of articles per issue

        Returns:
            Path to the output file
        """
        try:
            # Get all issue links
            print("Getting issue links...")
            issue_links = self.get_issue_links()

            # Load previous progress if resume_from is specified
            current_issue, processed_issues, all_articles_text = None, [], ""
            if self.resume_from:
                print(f"Attempting to resume from issue: {self.resume_from}")
                current_issue, processed_issues, all_articles_text = self.load_progress()

                # If we have a specific issue to resume from, find it in the list
                if self.resume_from in issue_links:
                    start_idx = issue_links.index(self.resume_from)
                    issue_links = issue_links[start_idx:]
                    print(f"Resuming from issue {start_idx+1}/{len(issue_links)}")
                elif processed_issues:
                    # Filter out already processed issues
                    issue_links = [url for url in issue_links if url not in processed_issues]
                    print(f"Resuming with {len(issue_links)} remaining issues")

            # Limit issues if specified
            if limit_issues and limit_issues > 0:
                issue_links = issue_links[:limit_issues]
                print(f"Limited to first {limit_issues} issues")

            if not all_articles_text:
                all_articles_text = ""

            processed_count = 0
            total_articles = 0
            newly_processed_issues = []

            # Process each issue
            for issue_idx, issue_url in enumerate(issue_links):
                print(f"\n{'='*80}\nProcessing issue {issue_idx+1}/{len(issue_links)}: {issue_url}\n{'='*80}")

                # Get article links and data from issue
                article_data_list = self.get_article_links_from_issue(issue_url)

                # Limit articles if specified
                if limit_articles and limit_articles > 0:
                    article_data_list = article_data_list[:limit_articles]
                    print(f"Limited to first {limit_articles} articles in this issue")

                issue_articles_processed = 0

                # Process each article
                for article_idx, article_data in enumerate(article_data_list):
                    total_articles += 1
                    print(f"\n{'-'*80}\nProcessing article {article_idx+1}/{len(article_data_list)}: {article_data.get('title', 'Unknown title')}\n{'-'*80}")

                    # Process article (download PDF, extract text, format)
                    article_text = self.process_article(article_data)
                    
                    # Skip if article was filtered out due to language
                    if article_text is None:
                        print(f"Article skipped (language filter): {article_data.get('title', 'Unknown')}")
                        continue

                    # Add to overall text
                    all_articles_text += article_text
                    processed_count += 1
                    issue_articles_processed += 1

                    logger.info(f"Processed article: {article_data.get('title')}")
                    print(f"Successfully processed article: {article_data.get('title')}")

                    # Save progress periodically
                    if processed_count % self.save_interval == 0:
                        newly_processed_issues.append(issue_url)
                        all_processed = processed_issues + newly_processed_issues
                        self.save_progress(issue_url, all_processed, all_articles_text)

                        # Reconnect session to avoid timeout
                        self.update_session_headers()

                    # Add a small delay to avoid overwhelming the server
                    delay = random.uniform(2, 5)  # Random delay between 2-5 seconds
                    time.sleep(delay)

                # Mark this issue as fully processed
                if issue_articles_processed > 0 and issue_url not in newly_processed_issues:
                    newly_processed_issues.append(issue_url)
                    all_processed = processed_issues + newly_processed_issues
                    self.save_progress(issue_url, all_processed, all_articles_text)

            # Save all articles to a single file
            output_file = os.path.join(self.output_dir, 'all_articles.txt')
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(all_articles_text)

            logger.info(f"All articles saved to {output_file}")
            print(f"\nScraping completed! Processed {processed_count} of {total_articles} articles.")
            print(f"All articles saved to {output_file}")

            return output_file

        except Exception as e:
            print(f"Error during scraping: {e}")
            import traceback
            traceback.print_exc()
            # Save current progress before exiting
            if 'issue_url' in locals() and 'processed_issues' in locals():
                self.save_progress(issue_url, 
                                   processed_issues + newly_processed_issues if 'newly_processed_issues' in locals() else processed_issues,
                                   all_articles_text if 'all_articles_text' in locals() else "")
            raise

        finally:
            # Always close Chrome driver if it was opened
            self.close_chrome_driver()

# Function to run the scraper locally
def run_local_scraper(limit_issues=None, limit_articles=None, save_interval=10, resume_from=None):
    """
    Run the local scraper with specified parameters.

    Args:
        limit_issues: Optional limit on number of issues to process
        limit_articles: Optional limit on number of articles per issue
        save_interval: Number of articles after which to save progress
        resume_from: Optional issue URL to resume scraping from

    Returns:
        Path to the output file
    """
    print("Starting the POF Journal Scraper (Local Version)...")
    scraper = POFJournalLocalScraper()

    # Add save_interval and resume parameters
    scraper.save_interval = save_interval
    scraper.resume_from = resume_from

    return scraper.scrape_and_process(limit_issues, limit_articles)

# Main execution
if __name__ == "__main__":
    # For scraping the entire site, set all limits to None
    output_file = run_local_scraper(
        limit_issues=None,     # Scrape all issues
        limit_articles=None,   # Scrape all articles in issue
        save_interval=10       # Save progress after every 10 articles
    )
    print(f"Scraping completed! Output file: {output_file}")