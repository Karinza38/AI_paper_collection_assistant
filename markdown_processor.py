import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, TextLexer
from bs4 import BeautifulSoup
import re


class MarkdownProcessor:
    def __init__(self):
        # Initialize markdown with comprehensive extensions
        self.md = markdown.Markdown(
            extensions=[
                "extra",  # Tables, attr_list, fenced_code, footnotes
                "codehilite",  # Syntax highlighting
                "mdx_math",  # LaTeX math support
                "nl2br",  # Newlines to <br>
                "sane_lists",  # Better list handling
                "smarty",  # Smart quotes, dashes, etc.
                "toc",  # Table of contents
                "meta",  # Metadata
                "admonition",  # Admonitions/callouts
                "def_list",  # Definition lists
            ],
            extension_configs={
                "codehilite": {
                    "css_class": "highlight",
                    "linenums": False,
                    "guess_lang": False,
                },
                "mdx_math": {
                    "enable_dollar_delimiter": True,  # Enable $...$ for inline math
                    "add_preview": True,  # Add preview for math formulas
                },
            },
        )

        # Initialize Pygments formatter
        self.formatter = HtmlFormatter(
            style="monokai", cssclass="highlight", linenos=False
        )

    def process_content(self, content: str) -> str:
        """Process markdown content with enhanced formatting"""
        try:
            # Pre-process the content
            content = self._preprocess_content(content)

            # Convert markdown to HTML
            html = self.md.convert(content)

            # Post-process the HTML
            html = self._postprocess_html(html)

            return html

        except Exception as e:
            print(f"Error processing markdown: {e}")
            # Return sanitized original content if processing fails
            return f"<pre>{content}</pre>"

    def _preprocess_content(self, content: str) -> str:
        """Pre-process the markdown content"""
        # Normalize line endings
        content = content.replace("\r\n", "\n")

        # Fix code blocks
        content = re.sub(r"```(\w+)?\n", r"```\1\n", content)

        # Ensure proper spacing for lists
        content = re.sub(r"(?<=\n)[-*+] ", "\n* ", content)

        # Fix math delimiters
        content = re.sub(r"\$\$(.*?)\$\$", r"\n\n$$\1$$\n\n", content, flags=re.DOTALL)
        content = re.sub(r"(?<!\\)\$([^$]+?)\$", r"\\(\1\\)", content)

        return content

    def _postprocess_html(self, html: str) -> str:
        """Post-process the HTML content"""
        soup = BeautifulSoup(html, "html.parser")

        # Process code blocks with Pygments
        for pre in soup.find_all("pre"):
            if code := pre.find("code"):
                lang = (
                    code.get("class", [""])[0].replace("language-", "")
                    if code.get("class")
                    else ""
                )
                try:
                    lexer = get_lexer_by_name(lang) if lang else TextLexer()
                    highlighted = highlight(code.string or "", lexer, self.formatter)
                    new_pre = BeautifulSoup(highlighted, "html.parser")
                    pre.replace_with(new_pre)
                except (ValueError, KeyError) as e:
                    print(f"Error highlighting code block: {e}")
                    continue

        # Add CSS classes for styling
        self._add_css_classes(soup)

        return str(soup)

    def _add_css_classes(self, soup):
        """Add CSS classes to HTML elements"""
        # Headers
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            tag["class"] = tag.get("class", []) + ["heading", f"heading-{tag.name}"]

        # Lists
        for tag in soup.find_all(["ul", "ol"]):
            tag["class"] = tag.get("class", []) + ["list"]

        # Code blocks
        for tag in soup.find_all("pre"):
            tag["class"] = tag.get("class", []) + ["code-block"]

        # Inline code
        for tag in soup.find_all("code"):
            if "highlight" not in tag.get("class", []):
                tag["class"] = tag.get("class", []) + ["inline-code"]

        # Math blocks
        for tag in soup.find_all("div", class_="math"):
            tag["class"] = tag.get("class", []) + ["math-block"]

        # Tables
        for tag in soup.find_all("table"):
            tag["class"] = tag.get("class", []) + ["table"]

    def get_css(self) -> str:
        """Get the CSS required for styling"""
        return f"""
        {self.formatter.get_style_defs()}
        
        .heading {{ margin: 1em 0; font-weight: bold; }}
        .heading-h1 {{ font-size: 2em; }}
        .heading-h2 {{ font-size: 1.5em; }}
        .heading-h3 {{ font-size: 1.17em; }}
        
        .list {{ margin: 1em 0; padding-left: 2em; }}
        
        .code-block {{ 
            background: #f8f9fa;
            padding: 1em;
            border-radius: 4px;
            overflow-x: auto;
        }}
        
        .inline-code {{
            background: #f8f9fa;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-size: 0.9em;
        }}
        
        .math-block {{
            overflow-x: auto;
            padding: 1em 0;
        }}
        
        .table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }}
        
        .table th, .table td {{
            border: 1px solid #ddd;
            padding: 0.5em;
        }}
        """
