import os
import re
import yaml
import logging
from datetime import datetime, date
from typing import List, Dict, Any
import ebooklib
from ebooklib import epub
from markdown import markdown
import glob

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EPUBBuilder:
    def __init__(self, posts_dir: str = "posts", output_dir: str = "epub"):
        self.posts_dir = posts_dir
        self.output_dir = output_dir
        self.book = epub.EpubBook()
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        # Set default metadata
        self.book.set_identifier('lj-scraper-epub')
        self.book.set_title('LiveJournal Posts Collection')
        self.book.set_language('ru')
        self.book.add_author('evo-lutio')

    def parse_markdown_metadata(self, content: str) -> Dict[str, Any]:
        """Extract YAML front matter from markdown content."""
        metadata = {}
        if content.startswith('---'):
            try:
                # Find the end of YAML front matter
                end_yaml = content.find('---', 3)
                if end_yaml != -1:
                    yaml_content = content[3:end_yaml].strip()
                    metadata = yaml.safe_load(yaml_content)
            except Exception as e:
                logger.error(f"Error parsing YAML metadata: {str(e)}")
        return metadata

    def convert_markdown_to_html(self, content: str) -> str:
        """Convert markdown content to HTML."""
        # Remove YAML front matter if present
        if content.startswith('---'):
            end_yaml = content.find('---', 3)
            if end_yaml != -1:
                content = content[end_yaml + 3:].strip()
        
        # Remove the first h1 and date paragraph if they exist
        lines = content.split('\n')
        filtered_lines = []
        skip_next = False
        
        for line in lines:
            if skip_next:
                skip_next = False
                continue
                
            # Skip h1 headers
            if line.startswith('# '):
                skip_next = True  # Skip the next line (usually the date)
                continue
                
            # Skip date lines
            if re.match(r'^\d{4}-\d{2}-\d{2}$', line.strip()):
                continue
                
            filtered_lines.append(line)
        
        content = '\n'.join(filtered_lines)
        
        # Convert markdown to HTML
        html = markdown(content, extensions=['extra'])
        return html

    def create_chapter(self, title: str, content: str, date: str, prev_post: tuple = None, next_post: tuple = None) -> epub.EpubHtml:
        """Create an EPUB chapter from markdown content."""
        # Extract URL from metadata if present
        url = ""
        if content.startswith('---'):
            end_yaml = content.find('---', 3)
            if end_yaml != -1:
                yaml_content = content[3:end_yaml].strip()
                try:
                    metadata = yaml.safe_load(yaml_content)
                    url = metadata.get('url', '')
                except:
                    pass
        
        # Get content after YAML front matter
        if content.startswith('---'):
            end_yaml = content.find('---', 3)
            if end_yaml != -1:
                content = content[end_yaml + 3:].strip()
        
        # Remove markdown headers and dates
        lines = content.split('\n')
        filtered_lines = []
        skip_next = False
        
        for line in lines:
            if skip_next:
                skip_next = False
                continue
                
            # Skip h1 headers
            if line.startswith('# '):
                skip_next = True  # Skip the next line (usually the date)
                continue
                
            # Skip date lines
            if re.match(r'^\d{4}-\d{2}-\d{2}$', line.strip()):
                continue
                
            # Skip URL if it matches the one from metadata
            if url and (line.strip() == url or url in line):
                continue
                
            filtered_lines.append(line)
        
        content = '\n'.join(filtered_lines)
        
        # Convert markdown to HTML
        html_content = markdown(content, extensions=['extra'])
        
        # Remove any remaining h1 and date elements
        html_content = re.sub(r'<h1[^>]*>.*?</h1>', '', html_content)
        html_content = re.sub(r'<p class="date">.*?</p>', '', html_content)
        
        # Remove any raw text that matches the title or date
        html_content = re.sub(re.escape(title), '', html_content)
        html_content = re.sub(re.escape(date), '', html_content)
        
        # Remove any links that contain the URL
        if url:
            html_content = re.sub(f'<a[^>]*>{re.escape(url)}</a>', '', html_content)
            html_content = re.sub(f'<a[^>]*href="{re.escape(url)}"[^>]*>.*?</a>', '', html_content)
        
        # Remove empty HTML elements and clean up whitespace
        html_content = re.sub(r'<[^>]*>\s*</[^>]*>', '', html_content)
        html_content = re.sub(r'^\s+', '', html_content, flags=re.MULTILINE)  # Remove leading whitespace
        html_content = re.sub(r'\n\s*\n', '\n', html_content)  # Remove empty lines
        html_content = html_content.strip()  # Remove leading/trailing whitespace
        
        # Remove the first paragraph tag if it exists
        if html_content.startswith('<p>'):
            html_content = html_content[3:]
        if html_content.endswith('</p>'):
            html_content = html_content[:-4]
        
        # Create navigation links
        nav_links = '<div class="post-navigation">'
        if prev_post:
            nav_links += f'<a href="{prev_post[1]}" class="nav-link prev">← {prev_post[0]}</a>'
        if next_post:
            nav_links += f'<a href="{next_post[1]}" class="nav-link next">{next_post[0]} →</a>'
        nav_links += '</div>'
        
        # Create chapter
        chapter = epub.EpubHtml(title=title, file_name=f'chapter_{date}.xhtml')
        
        # Create URL section with a clear separator
        url_section = ''
        if url:
            url_section = f'''
                <div class="url-section">
                    <div class="url-container">
                        <a href="{url}" class="post-url">{url}</a>
                    </div>
                </div>
            '''
        
        # Clean up any remaining empty elements and whitespace
        content = f'''
            <h1 id="top">{title}</h1>
            <p class="date">{date}</p>
            {url_section}
            <div class="spacer">
            <p></p>
            </div>
            <div class="post-content">
                {html_content}
            </div>
        '''
        
        # Remove any empty elements and clean up whitespace
        content = re.sub(r'<[^>]*>\s*</[^>]*>', '', content)
        content = re.sub(r'^\s+', '', content, flags=re.MULTILINE)
        content = re.sub(r'\n\s*\n', '\n', content)
        content = content.strip()
        
        chapter.content = content
        
        return chapter

    def create_tag_posts_page(self, tag: str, posts: list) -> epub.EpubHtml:
        """Create a page listing all posts for a specific tag."""
        html_content = f'<h1>Posts tagged with: {tag}</h1>'
        html_content += '<div class="back-link"><a href="tags.xhtml">← Back to Tags</a></div>'
        html_content += '<ul class="tag-posts">'
        
        # Sort posts by date (assuming the filename contains the date)
        sorted_posts = sorted(posts, key=lambda x: x[1], reverse=True)
        
        for post_title, post_file in sorted_posts:
            html_content += f'<li><a href="{post_file}">{post_title}</a></li>'
        
        html_content += '</ul>'
        
        # Create the tag posts page
        tag_page = epub.EpubHtml(title=f'Posts: {tag}', file_name=f'tag_{tag}.xhtml')
        tag_page.content = html_content
        
        return tag_page

    def create_toc_page(self, posts_by_year: dict, all_tags: set = None, tag_to_posts: dict = None) -> epub.EpubHtml:
        """Create a table of contents page organized by year."""
        html_content = '<h1>Table of Contents</h1>'
        
        # Add link to Tags page if tags exist
        if all_tags:
            html_content += '<div class="toc-section">'
            html_content += '<h2><a href="tags.xhtml">Tags</a></h2>'
            html_content += '</div>'
        
        # Add posts by year
        html_content += '<div class="toc-section">'
        html_content += '<h2>Posts by Year</h2>'
        for year, posts in sorted(posts_by_year.items(), reverse=True):
            html_content += f'<div class="toc-year">'
            html_content += f'<h3>{year}</h3>'
            html_content += '<ul class="toc-posts">'
            
            for post_title, post_file in posts:
                html_content += f'<li><a href="{post_file}">{post_title}</a></li>'
            
            html_content += '</ul></div>'
        html_content += '</div>'
        
        toc_page = epub.EpubHtml(title='Table of Contents', file_name='toc.xhtml')
        toc_page.content = html_content
        
        return toc_page

    def create_tags_page(self, tags: set, tag_to_posts: dict) -> epub.EpubHtml:
        """Create the main tags page with clickable tags."""
        # Sort tags alphabetically
        sorted_tags = sorted(tags)
        
        # Create HTML content for tags page
        html_content = '<h1>Tags</h1>'
        html_content += '<div class="back-link"><a href="toc.xhtml">← Back to Table of Contents</a></div>'
        html_content += '<div class="tags-cloud">'
        
        for tag in sorted_tags:
            freq = len(tag_to_posts[tag])
            html_content += f'<div class="tag">'
            html_content += f'<a href="tag_{tag}.xhtml">{tag}</a>'
            html_content += f'<span class="tag-count">({freq})</span>'
            html_content += '</div>'
        
        html_content += '</div>'
        
        # Create the tags page
        tags_page = epub.EpubHtml(title='Tags', file_name='tags.xhtml')
        tags_page.content = html_content
        
        return tags_page

    def build_epub(self, year: str = None) -> str:
        """Build EPUB from markdown files."""
        # Get all markdown files
        pattern = os.path.join(self.posts_dir, '*.md')
        if year:
            pattern = os.path.join(self.posts_dir, f'{year}-*.md')
        
        md_files = sorted(glob.glob(pattern))
        if not md_files:
            logger.warning(f"No markdown files found in {self.posts_dir}")
            return None

        # Process each markdown file
        chapters = []
        toc_items = []
        all_tags = set()
        blog_name = None
        tag_to_posts = {}  # Dictionary to map tags to posts
        posts_by_year = {}  # Dictionary to organize posts by year

        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse metadata
                metadata = self.parse_markdown_metadata(content)
                if not metadata:
                    logger.warning(f"No metadata found in {md_file}")
                    continue

                # Extract blog name from URL if not already set
                if not blog_name and 'url' in metadata:
                    url = metadata['url']
                    match = re.search(r'https?://([^.]+)\.livejournal\.com', url)
                    if match:
                        blog_name = match.group(1).replace('-', '_')

                # Get post date and year
                post_date = metadata.get('date', 'Unknown Date')
                if isinstance(post_date, (datetime, date)):
                    post_year = str(post_date.year)
                    post_date = post_date.strftime('%Y-%m-%d')
                else:
                    # Try to extract year from the date string
                    try:
                        post_year = post_date.split('-')[0] if '-' in post_date else 'Unknown'
                    except:
                        post_year = 'Unknown'
                
                # Precompute nav info
                prev_post = (chapters[-1].title, chapters[-1].file_name) if chapters else None

                # Store title and filename in advance (for next_post assignment)
                chapter_title = metadata.get('title', 'Untitled')
                chapter_filename = f'chapter_{post_date}.xhtml'

                # next_post will be set later (once next chapter is created)

                # Create chapter
                chapter = self.create_chapter(
                    chapter_title,
                    content,
                    post_date,
                    prev_post=prev_post,
                    next_post=None  # temporary
                )

                # Add chapter and track
                chapter.file_name = chapter_filename
                chapters.append(chapter)
                self.book.add_item(chapter)
                toc_items.append(epub.Link(chapter.file_name, chapter.title, chapter.id))
                
                # Organize posts by year
                if post_year not in posts_by_year:
                    posts_by_year[post_year] = []
                posts_by_year[post_year].append((chapter.title, chapter.file_name))

                # Collect tags and map them to posts
                if 'tags' in metadata and metadata['tags'] != 'None':
                    if isinstance(metadata['tags'], str):
                        tags = [tag.strip() for tag in metadata['tags'].split(',')]
                    else:
                        tags = metadata['tags']
                    all_tags.update(tags)
                    
                    # Map tags to posts
                    for tag in tags:
                        if tag not in tag_to_posts:
                            tag_to_posts[tag] = []
                        tag_to_posts[tag].append((chapter.title, chapter.file_name))

            except Exception as e:
                logger.error(f"Error processing {md_file}: {str(e)}")
                continue

        if not chapters:
            logger.error("No chapters were created")
            return None

        # Update next_post for all chapters except the last one
        for i in range(len(chapters) - 1):
            next_post = (chapters[i + 1].title, chapters[i + 1].file_name)
            # Update the chapter content with proper next_post
            chapter = self.create_chapter(
                chapters[i].title,
                chapters[i].content,
                chapters[i].file_name.split('_')[1].split('.')[0],
                prev_post=(chapters[i-1].title, chapters[i-1].file_name) if i > 0 else None,
                next_post=next_post
            )
            chapters[i].content = chapter.content

        # Create table of contents page
        toc_page = self.create_toc_page(posts_by_year, all_tags, tag_to_posts)
        self.book.add_item(toc_page)
        toc_items.insert(0, epub.Link(toc_page.file_name, 'Table of Contents', toc_page.id))

        # Create tags page and tag-specific pages if there are tags
        if all_tags:
            # Create main tags page
            tags_page = self.create_tags_page(all_tags, tag_to_posts)
            self.book.add_item(tags_page)
            toc_items.insert(1, epub.Link(tags_page.file_name, 'Tags', tags_page.id))
            
            # Create individual tag pages
            for tag in all_tags:
                tag_page = self.create_tag_posts_page(tag, tag_to_posts[tag])
                self.book.add_item(tag_page)

        # Create table of contents
        self.book.toc = toc_items

        # Add default NCX and Nav files
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())

        # Read CSS from external file
        try:
            with open('style.css', 'r', encoding='utf-8') as f:
                style = f.read()
        except FileNotFoundError:
            logger.warning("style.css not found, using default styles")
            style = '''
            body {
                font-family: Cambria, Liberation Serif, Bitstream Vera Serif, Georgia, Times, Times New Roman, serif;
                margin: 2em;
                font-size: 1.1em;
                line-height: 1.6;
            }
            h1 {
                text-align: center;
                margin-bottom: 1em;
                color: #2c5282;
                margin-top: 2em;
            }
            h2 {
                color: #444;
                border-bottom: 1px solid #ddd;
                padding-bottom: 0.5em;
                margin-top: 2em;
                margin-bottom: 1em;
            }
            h3 {
                color: #666;
                margin-top: 2em;
                margin-bottom: 1em;
            }
            p {
                margin-bottom: 1em;
            }
            '''
        
        css = epub.EpubItem(
            uid="style_default",
            file_name="style/default.css",
            media_type="text/css",
            content=style
        )
        self.book.add_item(css)

        # Collect all tag pages for the spine
        tag_pages = []
        if all_tags:
            tag_pages.append(tags_page)
            for tag in all_tags:
                tag_page = self.create_tag_posts_page(tag, tag_to_posts[tag])
                self.book.add_item(tag_page)
                tag_pages.append(tag_page)

        # Create spine: nav, TOC, Tags, all tag pages, then chapters
        self.book.spine = ['nav', toc_page] + tag_pages + chapters

        # Generate filename using blog name
        if not blog_name:
            blog_name = "lj_posts"  # fallback if no blog name found
        
        if year:
            filename = f"{blog_name}_posts_{year}.epub"
        else:
            filename = f"{blog_name}_posts.epub"
        output_path = os.path.join(self.output_dir, filename)

        # Write EPUB file
        try:
            epub.write_epub(output_path, self.book, {})
            logger.info(f"Successfully created EPUB: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error writing EPUB file: {str(e)}")
            return None

def main():
    builder = EPUBBuilder()
    # Build EPUB for all posts
    builder.build_epub()
    # Build EPUB for specific year
    # builder.build_epub("2018")

if __name__ == "__main__":
    main() 