import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import re
import logging
from dateutil import parser
import calendar
import json
from typing import Dict, Any
from login import login
from getpass import getpass

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_config(config: Dict[str, Any]) -> None:
    """Validate the configuration dictionary."""
    required_fields = {
        'blog_url': str,
        'login': bool,
        'date_range': dict,
        'included_tags': list,
        'excluded_tags': list,
        'output_dir': str,
        'scraping_settings': dict
    }
    
    # Check required fields
    for field, field_type in required_fields.items():
        if field not in config:
            raise ValueError(f"Missing required field: {field}")
        if not isinstance(config[field], field_type):
            raise ValueError(f"Invalid type for {field}: expected {field_type.__name__}")
    
    # Validate date_range
    date_range = config['date_range']
    if 'start_date' not in date_range or 'end_date' not in date_range:
        raise ValueError("date_range must contain start_date and end_date")
    
    try:
        start_date = parser.parse(date_range['start_date'])
        end_date = parser.parse(date_range['end_date'])
        if start_date > end_date:
            raise ValueError("start_date must be before end_date")
    except Exception as e:
        raise ValueError(f"Invalid date format: {str(e)}")
    
    # Validate tag fields
    if not isinstance(config['included_tags'], list):
        raise ValueError("included_tags must be a list")
    if not isinstance(config['excluded_tags'], list):
        raise ValueError("excluded_tags must be a list")
    
    # Check for conflicting tags (same tag in both included and excluded)
    conflicting_tags = set(config['included_tags']) & set(config['excluded_tags'])
    if conflicting_tags:
        raise ValueError(f"Conflicting tags found in both included_tags and excluded_tags: {conflicting_tags}")
    
    # Validate scraping_settings
    required_scraping_settings = {
        'max_retries': int,
        'request_timeout': (int, float),
        'request_delay': (int, float),
        'max_pages': int
    }
    
    for setting, setting_type in required_scraping_settings.items():
        if setting not in config['scraping_settings']:
            raise ValueError(f"Missing required scraping setting: {setting}")
        if not isinstance(config['scraping_settings'][setting], setting_type):
            raise ValueError(f"Invalid type for {setting}: expected {setting_type.__name__}")

def load_config(config_path: str = 'config.json') -> Dict[str, Any]:
    """Load and validate configuration from JSON file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        validate_config(config)
        logger.info("Configuration loaded successfully")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file '{config_path}' not found")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {str(e)}")
        raise
    except ValueError as e:
        logger.error(f"Configuration validation failed: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading configuration: {str(e)}")
        raise

class LJScraper:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.blog_url = config['blog_url']
        self.base_url = self.blog_url # Not clear why we have blog_url and base_url
        self.journal_name = self.blog_url.split(".")[0].replace("https://", '')
        self.login = config['login']
        self.output_dir = config['output_dir'] + os.path.sep + self.journal_name
        self.start_date = parser.parse(config['date_range']['start_date'])
        self.end_date = parser.parse(config['date_range']['end_date'])
        self.included_tags = config['included_tags']
        self.excluded_tags = config['excluded_tags']
        self.scraping_settings = config['scraping_settings']
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"Created output directory: {self.output_dir}")
        
        if self.login:
            print("Authentication with LiveJournal requested")
            username = input("Enter LiveJournal Username: ")
            password = getpass("Enter LiveJournal password: ")
            self.cookies = login(username, password)
        else:
            print("Authentication not requested - only public posts will be scraped")
            self.cookies = {}

    def get_page_content(self, url):
        """Fetch the content of a page with error handling and retries."""
        for attempt in range(self.scraping_settings['max_retries']):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, cookies=self.cookies, timeout=self.scraping_settings['request_timeout'])
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                if attempt == self.scraping_settings['max_retries'] - 1:
                    logger.error(f"Failed to fetch {url} after {self.scraping_settings['max_retries']} attempts: {e}")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff

    def get_post_urls(self, skip=0):
        """Get post URLs from the main page using skip parameter for pagination."""
        url = f"{self.base_url}/?skip={skip}"
        content = self.get_page_content(url)
        if not content:
            return []

        soup = BeautifulSoup(content, 'html.parser')
        post_urls = []
        # Each post is in a div with class 'entry' or 'b-singlepost'
        post_divs = soup.find_all('div', class_=lambda c: c and ('entry' in c or 'b-singlepost' in c))
        
        for post_div in post_divs:
            # Find the date first to check if we should process this post
            date_elem = (
                post_div.find('time', class_='b-singlepost-author-date') or
                post_div.find('time', class_='entry-date') or
                post_div.find('time', class_='b-singlepost-date') or
                post_div.find('span', class_='b-singlepost-date') or
                post_div.find('time', class_='b-singlepost-date-text')
            )
            
            if date_elem:
                try:
                    post_date = parser.parse(date_elem.text.strip())
                    # Skip if post is before start date
                    if self.start_date and post_date < self.start_date:
                        logger.info(f"Found post from {post_date.strftime('%Y-%m-%d')} - before start date {self.start_date.strftime('%Y-%m-%d')}, stopping")
                        return []  # Return empty list to stop processing
                    # Skip if post is on or after end date
                    if self.end_date and post_date >= self.end_date:
                        continue
                except:
                    logger.warning(f"Could not parse date: {date_elem.text.strip()}")
                    continue
            
            # Only use the post title link
            title_link = post_div.find('a', href=True)
            if not title_link:
                continue
                
            post_url = title_link['href']
            # Skip profile URLs and non-post URLs
            if not post_url or '/profile/' in post_url or not post_url.startswith('http'):
                continue
                
            # Only include URLs from the same blog
            if not post_url.startswith(self.base_url):
                continue
                
            # Normalize by removing fragment
            post_url = post_url.split('#')[0]
            # Only include URLs that look like post URLs (contain numbers)
            if re.search(r'\d+\.html$', post_url):
                post_urls.append(post_url)
                
        logger.info(f"Found {len(post_urls)} post URLs at skip={skip}")
        return post_urls

    def extract_post_content(self, post_url):
        """Extract the main content of a post."""
        # Skip non-post URLs
        if not re.search(r'\d+\.html$', post_url):
            logger.info(f"Skipping non-post URL: {post_url}")
            return None
            
        full_post_url = post_url.split('#')[0]
        content = self.get_page_content(full_post_url)
        if not content:
            return None

        soup = BeautifulSoup(content, 'html.parser')
        
        # Find the post title
        title_elem = (
            soup.find('h1', class_='entry-title') or
            soup.find('h1', class_='b-singlepost-title') or
            soup.find('h1', class_='b-singlepost-title-link') or
            soup.find('h1', class_='b-singlepost-title-text') or
            soup.find('div', class_='subject')
        )
        if not title_elem:
            logger.info(f"Skipping page without title: {post_url}")
            return None
            
        title = title_elem.text.strip()
        logger.info(f"Found title: {title}")
        
        # Find the post date
        date_elem = (
            soup.find('time', class_='b-singlepost-author-date') or
            soup.find('time', class_='entry-date') or
            soup.find('time', class_='b-singlepost-date') or
            soup.find('span', class_='b-singlepost-date') or
            soup.find('time', class_='b-singlepost-date-text') or
            soup.find('div', class_='date')
        )
        if not date_elem:
            logger.info(f"Skipping page without date: {post_url}")
            return None
            
        # Extract date from the time element's text
        date_text = date_elem.text.strip()
        
        # With certain themes there can be an @ between the date and the time
        date_text = date_text.replace('@', '')
        
        # Parse the date using dateutil
        try:
            post_date = parser.parse(date_text)
            date = post_date.strftime("%Y-%m-%d")
            
            # Log the date comparison details
            logger.info(f"Date comparison for post {title}:")
            logger.info(f"- Post date: {date}")
            logger.info(f"- Start date: {self.start_date.strftime('%Y-%m-%d')}")
            logger.info(f"- End date: {self.end_date.strftime('%Y-%m-%d')}")
            
            # Check if post is within date range
            if self.start_date and post_date < self.start_date:
                logger.info(f"Found post from {date} - before start date {self.start_date.strftime('%Y-%m-%d')}, stopping")
                raise StopIteration  # This will be caught by the caller to stop processing
            
            if self.end_date and post_date >= self.end_date:
                logger.info(f"Found post from {date} - on or after end date {self.end_date.strftime('%Y-%m-%d')}, stopping")
                raise StopIteration  # Stop processing when we find posts after end date
                
            logger.info(f"Post date {date} is within range")
        except StopIteration:
            raise  # Re-raise StopIteration to be caught by the caller
        except:
            logger.info(f"Skipping page with invalid date: {post_url}")
            return None
            
        logger.info(f"Found date: {date}")

        # Find the tags
        tags_elem = (
            soup.find('div', class_='b-singlepost-tags') or
            soup.find('div', class_='entry-tags') or
            soup.find('ul', class_='b-singlepost-tags-list')
        )
        
        if tags_elem:
            # Extract all tags
            tags = [tag.text.strip() for tag in tags_elem.find_all('a')]
            logger.info(f"Found tags: {', '.join(tags)}")
            
            # Skip if any excluded tag is present
            if self.excluded_tags and any(tag in self.excluded_tags for tag in tags):
                logger.info(f"Skipping post with excluded tag(s): {', '.join(self.excluded_tags)}")
                return None
            
            # Skip if included_tags is specified and post doesn't have any of the required tags
            if self.included_tags and not any(tag in self.included_tags for tag in tags):
                logger.info(f"Skipping post without required tag(s): {', '.join(self.included_tags)}")
                return None
        else:
            logger.info("No tags found")
            tags = []
            
            # If included_tags is specified and post has no tags, skip it
            if self.included_tags:
                logger.info(f"Skipping post without tags (required tags: {', '.join(self.included_tags)})")
                return None
        
        # Find the main content using the most precise selector
        content_elem = soup.find('article', class_='b-singlepost-body entry-content e-content')
        if not content_elem:
            # Try less strict matching for the article
            articles = soup.find_all('article')
            for art in articles:
                classes = art.get('class', [])
                if 'b-singlepost-body' in classes and 'entry-content' in classes:
                    content_elem = art
                    break
        if not content_elem:
            # Fallback to previous logic
            content_elem = (
                soup.find('div', class_='entry-content') or
                soup.find('div', class_='b-singlepost-body') or
                soup.find('div', class_='b-singlepost-bodytext') or
                soup.find('div', class_='b-singlepost-body-text') or
                soup.find('div', class_='b-singlepost-body-text-wrapper') or
                soup.find('div', class_='entry_text')
            )
        if not content_elem:
            logger.error("Could not find content element")
            return None
        # Clean up the content
        for tag in content_elem.find_all(['script', 'style', 'iframe']):
            tag.decompose()
        for tag in content_elem.find_all('a', string=lambda s: s and ('Read more' in s or 'Читать дальше' in s)):
            tag.decompose()
        for tag in content_elem.find_all('div', class_='lj-cut'):
            tag.decompose()
        post_content = content_elem.get_text(separator='\n', strip=True)
        logger.info(f"Extracted content length: {len(post_content)} characters")
        return {
            'title': title,
            'date': date,
            'content': post_content,
            'url': full_post_url,
            'tags': tags
        }

    def save_post(self, post_data):
        """Save post content to a markdown file with structured format."""
        if not post_data:
            logger.error("Cannot save post: post_data is None")
            return False

        # Create a safe filename from the title
        safe_title = re.sub(r'[^\w\s-]', '', post_data['title'])
        safe_title = re.sub(r'[-\s]+', '-', safe_title).strip('-_')
        
        # Create filename with date prefix and .md extension
        filename = f"{post_data['date']}_{safe_title}.md"
        filepath = os.path.join(self.output_dir, filename)

        # Check if file already exists
        if os.path.exists(filepath):
            logger.warning(f"File already exists: {filename}")
            return False

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # Write YAML front matter
                f.write('---\n')
                f.write(f'title: {post_data["title"]}\n')
                f.write(f'date: {post_data["date"]}\n')
                f.write(f'url: {post_data["url"]}\n')
                # Always include tags, using "None" if no tags are present
                if post_data['tags']:
                    f.write(f'tags: {", ".join(post_data["tags"])}\n')
                else:
                    f.write('tags: None\n')
                f.write('---\n\n')
                
                # Write content with proper markdown formatting
                content = post_data['content']
                
                # Split content into paragraphs and format
                paragraphs = content.split('\n\n')
                formatted_content = '\n\n'.join(paragraphs)
                
                f.write(formatted_content)
                
            logger.info(f"Successfully saved post to {filename}")
            return True
        except IOError as e:
            logger.error(f"Error saving post {filename}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving post {filename}: {str(e)}")
            return False

    def get_post_urls_from_monthly_archive(self, year, month):
        """Get post URLs from a specific month's archive page."""
        url = f"{self.base_url}/{year}/{month:02d}/"
        logger.info(f"Fetching monthly archive: {url}")
        
        content = self.get_page_content(url)
        if not content:
            return []

        soup = BeautifulSoup(content, 'html.parser')
        post_urls = []
        
        # Find all post links in the monthly archive
        for link in soup.find_all('a', href=True):
            post_url = link['href']
            # Only include URLs that look like post URLs (contain numbers)
            if re.search(r'\d+\.html$', post_url):
                # Normalize by removing fragment
                post_url = post_url.split('#')[0]
                # Only include URLs from the same blog
                if post_url.startswith(self.base_url):
                    post_urls.append(post_url)
        
        # Remove duplicates while preserving order
        post_urls = list(dict.fromkeys(post_urls))
        logger.info(f"Found {len(post_urls)} unique post URLs in {year}/{month}")
        return post_urls

    def scrape_old_posts(self):
        """Scrape older posts using monthly archive structure."""
        if not self.start_date or not self.end_date:
            logger.error("Start and end dates are required for old posts scraping")
            return

        posts_saved = 0
        posts_attempted = 0
        current_year = self.start_date.year
        current_month = self.start_date.month

        while current_year <= self.end_date.year:
            while current_month <= 12:
                if current_year == self.end_date.year and current_month > self.end_date.month:
                    break

                if current_year == self.start_date.year and current_month < self.start_date.month:
                    current_month += 1
                    continue

                logger.info(f"Processing {current_year}/{current_month:02d}")
                post_urls = self.get_post_urls_from_monthly_archive(current_year, current_month)

                try:
                    for post_url in post_urls:
                        logger.info(f"Processing post: {post_url}")
                        post_data = self.extract_post_content(post_url)
                        posts_attempted += 1

                        if post_data:
                            if self.save_post(post_data):
                                posts_saved += 1
                                logger.info(f"Successfully saved post {posts_saved}")
                            else:
                                logger.warning(f"Failed to save post: {post_url}")
                        else:
                            logger.info(f"Skipped post: {post_url}")

                        time.sleep(self.scraping_settings['request_delay'])  # Be nice to the server
                except StopIteration:
                    logger.info("Reached end of date range, stopping gracefully")
                    break

                current_month += 1
                time.sleep(self.scraping_settings['request_delay'])  # Be nice to the server

            if posts_saved > 0 and posts_attempted > 0:
                break  # Stop if we've processed any posts and hit the date range

            current_year += 1
            current_month = 1

        # Count actual files in the posts directory
        actual_posts = len([f for f in os.listdir(self.output_dir) if f.endswith('.md')])
        logger.info(f"\nScraping completed:")
        logger.info(f"- Attempted to process {posts_attempted} posts")
        logger.info(f"- Successfully saved {posts_saved} posts")
        logger.info(f"- Found {actual_posts} files in {self.output_dir}/")
        if posts_saved != actual_posts:
            logger.warning(f"Discrepancy detected: saved {posts_saved} posts but found {actual_posts} files")

    def scrape_recent_posts(self):
        """Scrape recent posts using the skip parameter method."""
        page_num = 1
        posts_saved = 0
        posts_attempted = 0

        while page_num <= self.scraping_settings['max_pages']:
            logger.info(f"Fetching page {page_num}...")
            post_urls = self.get_post_urls(page_num)
            if not post_urls:
                logger.info("No more posts found.")
                break

            # Process each post URL immediately to check dates
            try:
                for post_url in post_urls:
                    logger.info(f"Processing post: {post_url}")
                    post_data = self.extract_post_content(post_url)
                    posts_attempted += 1
                    
                    if post_data:
                        if self.save_post(post_data):
                            posts_saved += 1
                            logger.info(f"Successfully saved post {posts_saved}")
                        else:
                            logger.warning(f"Failed to save post: {post_url}")
                    else:
                        logger.info(f"Skipped post: {post_url}")
                    
                    time.sleep(self.scraping_settings['request_delay'])  # Be nice to the server
            except StopIteration:
                logger.info("Reached end of date range, stopping gracefully")
                break
            
            page_num += 1
            time.sleep(self.scraping_settings['request_delay'])  # Be nice to the server

        # Count actual files in the posts directory
        actual_posts = len([f for f in os.listdir(self.output_dir) if f.endswith('.md')])
        logger.info(f"\nScraping completed:")
        logger.info(f"- Attempted to process {posts_attempted} posts")
        logger.info(f"- Successfully saved {posts_saved} posts")
        logger.info(f"- Found {actual_posts} files in {self.output_dir}/")
        if posts_saved != actual_posts:
            logger.warning(f"Discrepancy detected: saved {posts_saved} posts but found {actual_posts} files")

    def scrape_blog(self):
        """Choose the appropriate scraping method based on the date range."""
        current_year = datetime.now().year
        
        if self.start_date and self.start_date.year < current_year:
            logger.info("Using monthly archive method for older posts")
            self.scrape_old_posts()
        else:
            logger.info("Using recent posts method")
            self.scrape_recent_posts()

def main():
    try:
        config = load_config()
        scraper = LJScraper(config)
        scraper.scrape_blog()
    except StopIteration:
        logger.info("Scraping completed - reached date range limit")
    except Exception as e:
        logger.error(f"Failed to run scraper: {str(e)}")
        raise

if __name__ == "__main__":
    main() 
