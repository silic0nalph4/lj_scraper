# LiveJournal Blog Scraper & EPUB Builder

A comprehensive tool for scraping LiveJournal blogs and converting the posts into a formatted EPUB book with navigation, tags, and mobile-friendly styling.

## Features
### Scraper Features
- **Date Range Filtering**: Scrape posts within specific date ranges (e.g., June 1-30, 2025)
- **Tag Filtering**: 
  - Include posts with specific tags only
  - Exclude posts with specific tags
- **Error Handling**: Robust error handling with retry logic and detailed logging

### EPUB Builder Features
- Generate a **single EPUB book** with:
  - Table of Contents organized by year
  - Tags page with clickable tag cloud
  - Individual tag pages showing all posts for each tag
- **Mobile-Friendly**: Responsive design optimized for mobile devices
- **Metadata Preservation**: Maintains original post URLs and dates
- **Custom Styling**: External CSS file for easy customization

## Tech stack
- Python 3.6+
- Web Scraping & HTTP
    requests - HTTP library for making web requests
    BeautifulSoup4 - HTML/XML parsing library
- EPUB Generation
    ebooklib - EPUB file creation and manipulation

## Architecture
### Core Components
- LJScraper - Main scraping engine
- EPUBBuilder - EPUB generation engine
- Configuration System - JSON-based configuration
- Styling System - External CSS for EPUB formatting

### Data Flow
![Screenshot 2025-06-23 at 12 58 31 PM](https://github.com/user-attachments/assets/800b32f1-74b1-4029-82c0-7d453657ef95)

Input: HTML (LiveJournal pages)
Intermediate: Markdown with YAML front matter
Output: EPUB (eBook format)

## Installation
1. Clone this repository or download the files
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
### Step 1: Scraping Posts

Run the scraper to collect posts from the LiveJournal blog:

```bash
python lj_scraper.py
```

**Configuration Options:**
- Edit `config.json` to customize scraping parameters:
  ```json
  {
    "blog_url": "https://blog_name.livejournal.com/",
    "start_date": "2025-06-01",
    "end_date": "2025-06-30",
    "included_tags": [],
    "excluded_tags": ["exclude_tag"],
    "max_posts": 100
  }
  ```
**Scraped Posts**
Posts are saved in the `posts` directory with filenames in the format:
```
YYYY-MM-DD_Post-Title.md
```

### Step 2: Creating EPUB

After scraping, create a EPUB book:

```bash
python epub_builder.py
```

**EPUB Builder Options:**
- **All Posts**: Creates EPUB with all scraped posts
- **Year-Specific**: Create EPUB for a specific year:
  ```python
  builder.build_epub("2025")  # For posts from 2025 only
  ```


### Styling
Edit `style.css` to customize the EPUB appearance:
- Font sizes and families
- Colors and spacing
- Mobile responsiveness
- Tag cloud styling
- Navigation elements

### Configuration
Modify `config.json` for scraping preferences:
- Date ranges
- Tag exclusions
- Post limits
- Blog URLs

## File Structure

```
lj_scrapper/
├── lj_scraper.py          # Main scraper script
├── epub_builder.py        # EPUB creation script
├── config.json           # Scraping configuration
├── style.css             # EPUB styling
├── requirements.txt      # Python dependencies
├── posts/               # Scraped posts (markdown files)
└── epub/                # Generated EPUB files
```


### Logging
Both scripts provide detailed logging:
- Scraping progress and errors
- EPUB creation status
- File processing information

## Notes

- The scraper respects server load with appropriate delays
- EPUB files are optimized for both desktop and mobile reading
- All navigation is internal (no external links in tag pages)
- The system automatically handles Russian text and special characters
- Tag pages are properly integrated into the EPUB navigation structure 
