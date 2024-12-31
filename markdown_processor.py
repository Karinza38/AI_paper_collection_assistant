import markdown
from markdown.extensions import fenced_code, tables, attr_list
import re
from bs4 import BeautifulSoup

class MarkdownProcessor:
    def __init__(self):
        # Initialize markdown with extensions
        self.md = markdown.Markdown(extensions=[
            'extra',           # Includes tables, attr_list, etc.
            'nl2br',          # Converts newlines to <br>
            'sane_lists',     # Better list handling
            'fenced_code',    # For code blocks
            'attr_list',      # For adding attributes to elements
            'meta'            # For metadata
        ])
        
    def process_content(self, content: str) -> str:
        """Process markdown content with proper formatting"""
        
        # Pre-process the content
        content = self._preprocess_content(content)
        
        # Convert markdown to HTML
        html = self.md.convert(content)
        
        # Post-process the HTML
        html = self._postprocess_html(html)
        
        return html
    
    def _preprocess_content(self, content: str) -> str:
        """Pre-process the markdown content"""
        # Ensure proper spacing for bullet points
        content = re.sub(r'(?<=\n)\* ', '\n* ', content)
        
        # Ensure proper spacing between sections
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Fix nested bullet points
        content = re.sub(r'(\n\* .+)(\n {2,}\* .+)', r'\1\n    \2', content)
        
        return content
    
    def _postprocess_html(self, html: str) -> str:
        """Post-process the HTML content"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Add classes to elements
        for tag in soup.find_all(['ul', 'ol']):
            tag['class'] = tag.get('class', []) + ['list-disc', 'ml-4', 'mb-4']
            
        for tag in soup.find_all('li'):
            tag['class'] = tag.get('class', []) + ['mb-2']
            
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            tag['class'] = tag.get('class', []) + ['font-bold', 'mt-6', 'mb-4']
            
        for tag in soup.find_all('p'):
            tag['class'] = tag.get('class', []) + ['mb-4']
            
        for tag in soup.find_all('code'):
            tag['class'] = tag.get('class', []) + ['bg-gray-100', 'px-2', 'py-1', 'rounded']
            
        # Convert back to string
        return str(soup) 