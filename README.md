# LiveJournal Blog Scraper & EPUB Builder

A comprehensive tool for scraping LiveJournal blogs and converting the posts into a beautifully formatted EPUB book with navigation, tags, and mobile-friendly styling.

## Features

### Scraper Features
- **Smart Post Detection**: Automatically filters out profile URLs and non-post content
- **Date Range Filtering**: Scrape posts within specific date ranges (e.g., June 1-30, 2025)
- **Tag Filtering**: 
  - Include posts with specific tags only
  - Exclude posts with specific tags (e.g., "evolutiolab")
  - Empty arrays mean no filtering (include all posts for included_tags, no exclusions for excluded_tags)
- **Pagination Support**: Uses LiveJournal's `?skip` parameter for efficient pagination
- **Error Handling**: Robust error handling with retry logic and detailed logging
- **Respectful Scraping**: Implements delays to be respectful to the server

### EPUB Builder Features
- **Beautiful Formatting**: Clean, readable layout with proper typography
- **Navigation System**: 
  - Table of Contents organized by year
  - Tags page with clickable tag cloud
  - Individual tag pages showing all posts for each tag
  - Previous/Next post navigation
- **Mobile-Friendly**: Responsive design optimized for mobile devices
- **Metadata Preservation**: Maintains original post URLs and dates
- **Custom Styling**: External CSS file for easy customization
- **Blog Name Integration**: Automatically extracts blog name for EPUB filename

## Requirements

- Python 3.6 or higher
- Required packages (install using `pip install -r requirements.txt`):
  - requests
  - beautifulsoup4
  - python-dateutil
  - ebooklib
  - markdown
  - pyyaml

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
    "blog_url": "https://evo-lutio.livejournal.com/",
    "start_date": "2025-06-01",
    "end_date": "2025-06-30",
    "included_tags": [],
    "excluded_tags": ["evolutiolab"],
    "max_posts": 100
  }
  ```

**Scraper Features:**
- **Date Range**: Only scrapes posts within the specified date range
- **Tag Filtering**: 
  - `included_tags`: Only scrape posts with these tags (empty array = include all posts)
  - `excluded_tags`: Skip posts with these tags (empty array = no exclusions)
- **Smart Pagination**: Stops when encountering posts outside the date range
- **Detailed Logging**: Shows progress and any issues encountered

### Step 2: Creating EPUB

After scraping, create a beautiful EPUB book:

```bash
python epub_builder.py
```

**EPUB Builder Options:**
- **All Posts**: Creates EPUB with all scraped posts
- **Year-Specific**: Create EPUB for a specific year:
  ```python
  builder.build_epub("2025")  # For posts from 2025 only
  ```

**EPUB Features:**
- **Table of Contents**: Organized by year with clickable links
- **Tags Navigation**: 
  - Main tags page with tag cloud
  - Individual tag pages showing all posts for each tag
  - Back navigation between pages
- **Mobile Optimization**: Touch-friendly design with responsive typography
- **Custom Styling**: Uses `style.css` for consistent formatting

## Output Structure

### Scraped Posts
Posts are saved in the `posts` directory with filenames in the format:
```
YYYY-MM-DD_Post-Title.md
```

Each file contains:
- YAML metadata (title, date, URL, tags)
- Post content in markdown format

### Generated EPUB
EPUB files are saved in the `epub` directory with filenames like:
```
evo_lutio_posts.epub
evo_lutio_posts_2025.epub  # For year-specific builds
```

## Customization

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

## Advanced Usage

### Custom Date Ranges
```python
# In config.json
{
  "start_date": "2025-02-01",
  "end_date": "2025-12-31"
}
```

### Tag Filtering Examples
```python
# Include only posts with specific tags
{
  "included_tags": ["science", "technology"],
  "excluded_tags": []
}

# Exclude posts with specific tags (include all others)
{
  "included_tags": [],
  "excluded_tags": ["evolutiolab", "private", "draft"]
}

# Include posts with tag A but exclude posts with tag B
{
  "included_tags": ["public"],
  "excluded_tags": ["private", "draft"]
}

# No tag filtering (include all posts)
{
  "included_tags": [],
  "excluded_tags": []
}
```

### Year-Specific EPUB
```python
# In epub_builder.py
builder = EPUBBuilder()
builder.build_epub("2024")  # Only 2024 posts
```

## Troubleshooting

### Common Issues
1. **No posts found**: Check the date range in `config.json`
2. **EPUB styling issues**: Ensure `style.css` exists and is readable
3. **Tag pages not working**: Verify that tag pages are included in the EPUB spine
4. **Mobile display problems**: Check the responsive CSS in `style.css`

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